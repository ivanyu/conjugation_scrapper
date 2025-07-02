# French Verb Conjugation Scraper

This Python script scrapes French verb conjugations from Wiktionary and outputs them in CSV format.

**100% vibe-coded with Claude Code**

## Features

- Scrapes conjugations for 8 specific tenses:
  - Indicatif: Présent, Imparfait, Passé simple, Passé composé, Futur simple
  - Subjonctif: Présent, Imparfait  
  - Conditionnel: Présent
- Uses the mobile version of Wiktionary for cleaner HTML parsing
- Extracts both conjugated forms and phonetic transcriptions
- Outputs in structured CSV format with proper IDs and tags
- Includes deduplication to avoid duplicate entries

## Requirements

- Python 3.6+
- requests
- beautifulsoup4
- lxml

## Installation

1. Create a virtual environment:
```bash
virtualenv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install requests beautifulsoup4 lxml
```

## Usage

```bash
python conjugation_scraper.py <input_file> <output_file>
```

- `input_file`: Text file with one verb per line (infinitive form)
- `output_file`: CSV file where conjugations will be written

### Example

```bash
python conjugation_scraper.py verbs.txt conjugations.csv
```

## Input Format

Create a text file with one verb per line:
```
être
voir
avoir
faire
```

## Output Format

The CSV output contains these columns:
1. **ID**: `<infinitive> - <mood> - <tense> - <person>_<number>`
2. **Infinitive**: The verb in infinitive form
3. **Conjugated form**: The conjugated verb
4. **Transcription**: Phonetic transcription
5. **Mood**: The grammatical mood (indicatif, subjonctif, conditionnel)
6. **Tense**: The grammatical tense (présent, imparfait, etc.)
7. **Person**: The person and number (première_singulier, deuxième_pluriel, etc.)

### Example output:
```csv
être - indicatif - présent - première_singulier,être,suis,\ʒə sɥi\,indicatif,présent,première_singulier
être - indicatif - présent - deuxième_singulier,être,es,\ty ɛ\,indicatif,présent,deuxième_singulier
dîner - indicatif - passé_composé - première_singulier,dîner,ai dîné,\ʒ‿e di.ne\,indicatif,passé composé,première_singulier
aller - indicatif - passé_composé - première_singulier,aller,suis allé,\ʒə sɥi.z‿a.le\,indicatif,passé composé,première_singulier
```

## Notes

- The script includes a small delay between requests to be respectful to Wiktionary servers
- Some verbs may not have all conjugations available on Wiktionary
- For Passé composé, the script correctly extracts auxiliary verbs (avoir/être) with past participles
- The script handles Unicode apostrophes (') from Wiktionary by converting them to regular apostrophes
- The script filters out reflexive and compound forms to focus on basic conjugations