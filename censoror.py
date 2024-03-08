import spacy
import argparse
import glob
import os
import re
import pyap

# phone_number_pattern = re.compile(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})')
phone_number_pattern = re.compile(r'((?:\+\d{1,2}[-\.\s]??)?(?:\d{4}[-\.\s]??)?(?:\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4}))')

# re.compile(r'((?:\+\d{2}[-\.\s]??|\d{4}[-\.\s]??)?(?:\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4}))')
def censor_spacy(text):
    nlp = spacy.load("en_core_web_md")
    doc = nlp(text)
    censored_text = text
    for ent in doc.ents:
        # "GPE", "LOC"
        if ent.label_ in ['PERSON', "DATE"]:
            print(ent.text, " ", ent.label_)
            censored_text = censored_text.replace(ent.text, '\u2588' * len(ent.text))
    matches = phone_number_pattern.findall(text)
    for numbers in matches:
        censored_text = censored_text.replace(numbers, '\u2588' * len(numbers))
    return censored_text

def censor_address(censored_text):
    addresses = pyap.parse(censored_text, country='US')
    for address in addresses:
        address_str = str(address)
        censored_text = censored_text.replace(address_str, '\u2588' * len(address_str))
    return censored_text


def main():
    parser = argparse.ArgumentParser(description="Censor sensitive information in plain text documents.")
    parser.add_argument('--input', required=True, help='Input file pattern (e.g., "*.txt").')
    parser.add_argument('--names', action='store_true', help='Censor names.')
    parser.add_argument('--dates', action='store_true', help='Censor dates.')
    parser.add_argument('--phones', action='store_true', help='Censor phone numbers.')
    parser.add_argument('--address', action='store_true', help='Censor addresses.')
    parser.add_argument('--output', required=True, help='Output folder for censored files.')
    parser.add_argument('--stats', required=True, help='File or location to write statistics.')
    args = parser.parse_args()
    input_files = glob.glob(args.input)
    for input_file in input_files:
        try:
            # Use the process_file function to handle each file
            process_file(input_file, args)
        except Exception as e:
            print(f"Error processing {input_file}: {e}")

    # Write statistics to the specified location
    with open(args.stats, 'w') as stats_file:
        stats_file.write("Statistics: ...")  # Add your statistics information here

def process_file(input_file, args):

    with open(input_file, 'r') as file:
        text_to_censor = file.read()
    res = ""
    res = censor_address(text_to_censor)
    res = censor_spacy(res)
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    output_file = os.path.join(args.output, os.path.splitext(os.path.basename(input_file))[0] + '.censored')

    # Write the censored content to the output file
    with open(output_file, 'w') as file:
        file.write(res)

if __name__ == '__main__':
    main()