#!/usr/bin/env python3
"""
French Verb Conjugation Scraper for Wiktionary
Scrapes French verb conjugations from Wiktionary and outputs them to CSV format.
"""

import requests
from bs4 import BeautifulSoup
import csv
import sys
import time
from urllib.parse import quote

class FrenchConjugationScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Mapping of tenses to their French names on Wiktionary
        self.tense_mapping = {
            'indicatif_présent': 'Présent',
            'indicatif_imparfait': 'Imparfait',
            'indicatif_passé_simple': 'Passé simple',
            'indicatif_futur_simple': 'Futur simple',
            'subjonctif_présent': 'Présent',
            'subjonctif_imparfait': 'Imparfait',
            'conditionnel_présent': 'Présent'
        }
        
        # Person order mapping
        self.persons = [
            ('première', 'singulier'),
            ('deuxième', 'singulier'), 
            ('troisième', 'singulier'),
            ('première', 'pluriel'),
            ('deuxième', 'pluriel'),
            ('troisième', 'pluriel')
        ]

    def get_conjugation_url(self, verb):
        """Generate Wiktionary conjugation URL for a verb."""
        encoded_verb = quote(verb, safe='')
        return f"https://fr.m.wiktionary.org/wiki/Conjugaison:français/{encoded_verb}"

    def fetch_page(self, url):
        """Fetch a webpage with error handling."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_conjugation_table(self, soup, verb):
        """Parse conjugation tables from the mobile HTML soup."""
        conjugations = []
        
        # Required tenses for each mood
        required_tenses = {
            'indicatif': ['Présent', 'Imparfait', 'Passé simple', 'Futur simple'],
            'subjonctif': ['Présent', 'Imparfait'],
            'conditionnel': ['Présent']
        }
        
        # Find all tables
        tables = soup.find_all('table')
        
        # Track current mood context
        current_mood = None
        
        for table in tables:
            # Check if this table is for a specific tense
            header_row = table.find('tr')
            if not header_row:
                continue
            
            headers = header_row.find_all(['th', 'td'])
            if not headers:
                continue
            
            tense_text = headers[0].get_text().strip()
            
            # Look for mood context in previous elements
            prev_elements = []
            current = table
            for _ in range(10):
                current = current.find_previous(['h2', 'h3', 'h4', 'p', 'div'])
                if not current:
                    break
                prev_elements.append(current.get_text().strip().lower())
            
            # Determine mood from context
            mood = None
            for text in prev_elements:
                if 'indicatif' in text:
                    mood = 'indicatif'
                    break
                elif 'subjonctif' in text:
                    mood = 'subjonctif'  
                    break
                elif 'conditionnel' in text:
                    mood = 'conditionnel'
                    break
            
            # If we found a relevant tense for the current mood
            if mood and tense_text in required_tenses.get(mood, []):
                # Extract conjugations from this table
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row_idx, row in enumerate(rows):
                    if row_idx >= len(self.persons):
                        break
                    
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    
                    # Mobile version pattern: pronoun | verb_form | pronunciation_start | pronunciation_end
                    conjugated_form = ""
                    pronunciation = ""
                    
                    if len(cells) >= 2:
                        conjugated_form = cells[1].get_text().strip()
                    
                    if len(cells) >= 4:
                        # Combine pronunciation parts, preserving spaces
                        pron_part1 = cells[2].get_text()  # Don't strip to preserve spaces
                        pron_part2 = cells[3].get_text()  # Don't strip to preserve backslashes
                        pronunciation = pron_part1 + pron_part2
                    elif len(cells) >= 3:
                        # Single pronunciation part
                        pronunciation = cells[2].get_text().strip()
                    
                    # Clean up the extracted data
                    if conjugated_form and conjugated_form not in ['—', '-', '']:
                        # Remove any trailing punctuation or whitespace
                        conjugated_form = conjugated_form.rstrip('.,!?;:')
                        
                        # Skip if this looks like a header
                        if conjugated_form.lower() in ['présent', 'imparfait', 'passé simple', 'futur simple']:
                            continue
                        
                        person, number = self.persons[row_idx]
                        person_number = f"{person}_{number}"
                        
                        # Create the ID
                        tense_name = tense_text.lower().replace(' ', '_')
                        conjugation_id = f"{verb} - {mood} - {tense_name} - {person_number}"
                        
                        conjugations.append({
                            'id': conjugation_id,
                            'infinitive': verb,
                            'conjugated_form': conjugated_form,
                            'transcription': pronunciation,
                            'mood': mood,
                            'tense': tense_text.lower(),
                            'person': person_number
                        })
        
        return conjugations

    def scrape_verb(self, verb):
        """Scrape conjugations for a single verb."""
        print(f"Scraping conjugations for: {verb}")
        
        url = self.get_conjugation_url(verb)
        html = self.fetch_page(url)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        conjugations = self.parse_conjugation_table(soup, verb)
        
        # Add small delay to be respectful
        time.sleep(0.5)
        
        return conjugations

    def scrape_verbs_from_file(self, input_file, output_file):
        """Scrape conjugations for verbs listed in input file and write to CSV."""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                verbs = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Error: Input file '{input_file}' not found.")
            return
        
        all_conjugations = []
        seen_ids = set()
        
        for verb in verbs:
            conjugations = self.scrape_verb(verb)
            # Deduplicate conjugations
            for conjugation in conjugations:
                if conjugation['id'] not in seen_ids:
                    all_conjugations.append(conjugation)
                    seen_ids.add(conjugation['id'])
        
        # Write to CSV
        self.write_csv(all_conjugations, output_file)
        print(f"Conjugations written to {output_file}")
        print(f"Total unique conjugations: {len(all_conjugations)}")

    def write_csv(self, conjugations, output_file):
        """Write conjugations to CSV file."""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            for conjugation in conjugations:
                writer.writerow([
                    conjugation['id'],
                    conjugation['infinitive'],
                    conjugation['conjugated_form'],
                    conjugation['transcription'],
                    conjugation['mood'],
                    conjugation['tense'],
                    conjugation['person']
                ])


def main():
    if len(sys.argv) != 3:
        print("Usage: python conjugation_scraper.py <input_file> <output_file>")
        print("  input_file: Text file with one verb per line")
        print("  output_file: CSV file to write conjugations to")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    scraper = FrenchConjugationScraper()
    scraper.scrape_verbs_from_file(input_file, output_file)


if __name__ == "__main__":
    main()