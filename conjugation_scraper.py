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
import re
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
            'indicatif': ['Présent', 'Imparfait', 'Passé simple', 'Passé composé', 'Futur simple'],
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
                    
                    # For Passé composé, combine auxiliary from first column with participle from second
                    if tense_text.lower() == 'passé composé' and len(cells) >= 2:
                        # First column contains pronoun + auxiliary (e.g., "j'ai", "tu as")
                        # Second column contains past participle (e.g., "dîné")
                        pronoun_aux = cells[0].get_text().strip().replace('\u2019', "'")  # Replace Unicode apostrophe
                        participle = cells[1].get_text().strip()
                        
                        # Extract just the auxiliary verb from pronoun + auxiliary
                        auxiliary = None
                        if pronoun_aux.startswith("j'") or pronoun_aux.startswith("J'"):
                            # For "j'ai" -> extract "ai"
                            aux_part = pronoun_aux.replace("j'", "").replace("J'", "").strip()
                            if not aux_part:
                                raise ValueError(f"Failed to extract auxiliary verb from '{pronoun_aux}' for verb '{verb}'")
                            auxiliary = aux_part
                        elif " " in pronoun_aux:
                            # For cases like "tu as", "il a", "nous avons", etc.
                            auxiliary = pronoun_aux.split()[-1]  # Get the last word (auxiliary)
                        
                        # Combine auxiliary + participle
                        if auxiliary and participle:
                            conjugated_form = f"{auxiliary} {participle}"
                        else:
                            raise ValueError(f"Failed to extract auxiliary ('{auxiliary}') or participle ('{participle}') for verb '{verb}' from pronoun_aux='{pronoun_aux}'")
                    
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

    def parse_sasseoir_conjugations(self, soup, verb):
        """Special handling for s'asseoir which has two conjugation variants."""
        conjugations = []

        # Find ALL pronominal conjugation tables for both variants
        tables = soup.find_all('table')
        assieds_tables = []
        assois_tables = []

        for i, table in enumerate(tables):
            table_text = table.get_text()
            if 'nous nous' in table_text:
                # Check for assieds/asseye variant (includes indicatif présent, subjonctif, conditionnel)
                if ('assieds' in table_text or 'assied' in table_text or
                    'asseyons' in table_text or 'asseyez' in table_text or 'asseyent' in table_text or
                    'asseye' in table_text or 'asseyions' in table_text or
                    'assiér' in table_text):  # assiérais, assiérait, etc. for conditionnel
                    assieds_tables.append(table)
                # Check for assois/assoie variant
                elif ('assois' in table_text or 'assoit' in table_text or
                      'assoyons' in table_text or 'assoyez' in table_text or 'assoient' in table_text or
                      'assoie' in table_text or 'assoyions' in table_text or
                      'assoiraient' in table_text):  # assoirais, assoirait, etc. for conditionnel
                    assois_tables.append(table)

        if not assieds_tables or not assois_tables:
            print(f"Warning: Could not find both conjugation variants for {verb}")
            return self.parse_conjugation_table(soup, verb)

        # Extract conjugations from ALL tables for both variants
        assieds_conjugations = []
        for table in assieds_tables:
            assieds_conjugations.extend(self._extract_pronominal_conjugations_from_table(table, verb, 'assieds'))

        assois_conjugations = []
        for table in assois_tables:
            assois_conjugations.extend(self._extract_pronominal_conjugations_from_table(table, verb, 'assois'))

        # Combine conjugations
        combined = {}
        for conj in assieds_conjugations:
            key = (conj['mood'], conj['tense'], conj['person'])
            combined[key] = {'assieds': conj}

        for conj in assois_conjugations:
            key = (conj['mood'], conj['tense'], conj['person'])
            if key in combined:
                combined[key]['assois'] = conj

        # Create combined entries with "ou"
        for key, variants in combined.items():
            if 'assieds' in variants and 'assois' in variants:
                assieds_form = variants['assieds']['conjugated_form']
                assois_form = variants['assois']['conjugated_form']

                # Combine with "ou" only if different
                if assieds_form != assois_form:
                    combined_form = f"{assieds_form} ou {assois_form}"
                else:
                    combined_form = assieds_form

                # Combine pronunciation (if available)
                pron1 = variants['assieds']['transcription']
                pron2 = variants['assois']['transcription']
                if pron1 and pron2 and pron1 != pron2:
                    combined_pron = f"{pron1} ou {pron2}"
                else:
                    combined_pron = pron1 if pron1 else pron2

                mood, tense, person = key
                conjugation_id = f"{verb} - {mood} - {tense} - {person}"

                conjugations.append({
                    'id': conjugation_id,
                    'infinitive': verb,
                    'conjugated_form': combined_form,
                    'transcription': combined_pron,
                    'mood': mood,
                    'tense': tense,
                    'person': person
                })

        return conjugations

    def _extract_pronominal_conjugations_from_table(self, table, verb, variant):
        """Extract conjugations from a pronominal table for s'asseoir."""
        conjugations = []

        # Required tenses for each mood
        required_tenses = {
            'indicatif': ['Présent', 'Imparfait', 'Passé simple', 'Passé composé', 'Futur simple'],
            'subjonctif': ['Présent', 'Imparfait'],
            'conditionnel': ['Présent']
        }

        # Find all sub-tables within this main table
        # Look for sections with mood context
        current_mood = None

        # Get all rows from the table
        all_rows = table.find_all('tr')

        # Track what we're currently parsing
        current_tense = None
        row_in_tense = 0

        for row_idx, row in enumerate(all_rows):
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue

            # Check if this is a header row (tense indicator)
            first_cell_text = cells[0].get_text().strip()

            # Detect mood from previous elements
            if current_mood is None:
                prev_elements = []
                current = table
                for _ in range(10):
                    current = current.find_previous(['h2', 'h3', 'h4'])
                    if not current:
                        break
                    prev_text = current.get_text().strip().lower()
                    if 'indicatif' in prev_text:
                        current_mood = 'indicatif'
                        break
                    elif 'subjonctif' in prev_text:
                        current_mood = 'subjonctif'
                        break
                    elif 'conditionnel' in prev_text:
                        current_mood = 'conditionnel'
                        break

            # Check if this is a tense header
            if first_cell_text in ['Présent', 'Imparfait', 'Passé simple', 'Passé composé', 'Futur simple']:
                current_tense = first_cell_text
                row_in_tense = 0
                continue

            # If we have a current tense and mood, extract data
            if current_tense and current_mood and current_tense in required_tenses.get(current_mood, []):
                if len(cells) >= 2:
                    # Extract pronoun and conjugated form
                    # Note: Replace non-breaking spaces with regular spaces
                    pronoun_cell = cells[0].get_text().strip().replace('\xa0', ' ')
                    form_cell = cells[1].get_text().strip()

                    # Get pronunciation if available
                    pronunciation = ""
                    if len(cells) >= 4:
                        pron_part1 = cells[2].get_text()
                        pron_part2 = cells[3].get_text()
                        pronunciation = pron_part1 + pron_part2
                    elif len(cells) >= 3:
                        pronunciation = cells[2].get_text().strip()

                    # Handle Passé composé specially
                    if current_tense == 'Passé composé':
                        # For pronominal verbs, format is: "je me suis" | "assis"
                        # We want: "me suis assis"
                        if ' ' in pronoun_cell:
                            parts = pronoun_cell.split()
                            if len(parts) >= 3:
                                # e.g., "je me suis" -> extract "me suis"
                                auxiliary_parts = ' '.join(parts[1:])  # "me suis"
                                conjugated_form = f"{auxiliary_parts} {form_cell}"
                            elif len(parts) == 2:
                                # e.g., "nous nous" or similar
                                conjugated_form = f"{parts[1]} {form_cell}"
                            else:
                                conjugated_form = f"{pronoun_cell} {form_cell}"
                        else:
                            conjugated_form = form_cell
                    else:
                        # For other tenses, extract the pronominal pronoun and verb
                        # Format examples:
                        # "je m'" | "assieds" -> "m'assieds"
                        # "nous nous" | "asseyons" -> "nous asseyons"
                        if ' ' in pronoun_cell:
                            parts = pronoun_cell.split()
                            if len(parts) >= 2:
                                pronominal_part = parts[-1]  # Get last part
                                # Check if it's "nous" or "vous" (repeated)
                                if pronominal_part in ['nous', 'vous']:
                                    # For "nous nous" or "vous vous", use just first part + space + verb
                                    conjugated_form = f"{pronominal_part} {form_cell}"
                                else:
                                    # For "je m'", "tu t'", "il/elle/on s'", "ils/elles s'"
                                    # Use pronominal pronoun attached to verb
                                    conjugated_form = f"{pronominal_part}{form_cell}"
                            else:
                                conjugated_form = form_cell
                        else:
                            conjugated_form = form_cell

                    # Clean up
                    if conjugated_form and conjugated_form not in ['—', '-', '']:
                        conjugated_form = conjugated_form.rstrip('.,!?;:')

                        # Map to person
                        if row_in_tense < len(self.persons):
                            person, number = self.persons[row_in_tense]
                            person_number = f"{person}_{number}"

                            tense_name = current_tense.lower().replace(' ', '_')

                            conjugations.append({
                                'conjugated_form': conjugated_form,
                                'transcription': pronunciation,
                                'mood': current_mood,
                                'tense': tense_name,
                                'person': person_number
                            })

                    row_in_tense += 1

                    # After 6 persons, we're done with this tense
                    if row_in_tense >= 6:
                        current_tense = None
                        row_in_tense = 0

        return conjugations

    def scrape_verb(self, verb):
        """Scrape conjugations for a single verb."""
        print(f"Scraping conjugations for: {verb}")

        url = self.get_conjugation_url(verb)
        html = self.fetch_page(url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')

        # Special handling for s’asseoir (with Unicode apostrophe U+2019)
        if verb == "s\u2019asseoir":
            conjugations = self.parse_sasseoir_conjugations(soup, verb)
        else:
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
                    conjugation['id'].replace('\u2019', "'"),
                    conjugation['infinitive'].replace('\u2019', "'"),
                    conjugation['conjugated_form'].replace('\u2019', "'"),
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