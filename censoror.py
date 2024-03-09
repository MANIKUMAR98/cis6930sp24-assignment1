import spacy
import argparse
import glob
import os
import phonenumbers
import pyap
import sys
import en_core_web_md

statistics = {}


def load_spacy():
    nlp = en_core_web_md.load()
    return nlp


def censor_name_and_date(text, nlp, input_file_name):
    censored_text = text
    try:
        doc = nlp(censored_text)
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                censored_text = censored_text.replace(ent.text, '\u2588' * len(ent.text))
                statistics[input_file_name]['names'] += 1
            elif ent.label_ == 'DATE':
                censored_text = censored_text.replace(ent.text, '\u2588' * len(ent.text))
                statistics[input_file_name]['dates'] += 1
        return censored_text
    except Exception as e:
        print("Exception occurred while censoring data using spacy ", e)
        return censored_text


def censor_phonenumbers(text, input_file_name):
    numbers_text = text
    try:
        for match in phonenumbers.PhoneNumberMatcher(text, "US"):
            original_format = match.raw_string
            numbers_text = numbers_text.replace(original_format, '\u2588' * len(original_format))
            statistics[input_file_name]['phone_numbers'] += 1
        return numbers_text
    except Exception as e:
        print("Exception occurred while censoring phone numbers ", e)
        return numbers_text


def censor_address(censored_text, input_file_name):
    try:
        addresses = pyap.parse(censored_text, country='US')
        for address in addresses:
            address_str = str(address)
            censored_text = censored_text.replace(address_str, '\u2588' * len(address_str))
            statistics[input_file_name]['addresses'] += 1
        return censored_text
    except Exception as e:
        print("Exception occurred while censoring addresses ", e)
        return censored_text


def write_data_to_stats(stats, file_count):
    if stats == "stderr":
        sys.stderr.write("Censoring Statistics:\n")
        sys.stderr.write("---------------------\n")
        sys.stderr.write("Total Files Processed: " + str(file_count) + "\n")
        sys.stderr.write("---------------------\n")
        for key, value in statistics.items():
            sys.stderr.write("File Name: " + key + "\n" + "-Censored Details: \n")
            for stat_key, stat_value in value.items():
                sys.stderr.write(f" -{stat_key.capitalize()}: {stat_value}\n")
            sys.stderr.write("---------------------\n")
    elif stats == "stdout":
        sys.stdout.write("Censoring Statistics:\n")
        sys.stdout.write("---------------------\n")
        sys.stdout.write("Total Files Processed: " + str(file_count) + "\n")
        sys.stdout.write("---------------------\n")
        for key, value in statistics.items():
            sys.stdout.write("File Name: " + key + "\n" + "-Censored Details: \n")
            for stat_key, stat_value in value.items():
                sys.stdout.write(f" -{stat_key.capitalize()}: {stat_value}\n")
            sys.stdout.write("---------------------\n")
    else:
        with open(stats, 'w') as file:
            file.write("Censoring Statistics:\n")
            file.write("---------------------\n")
            file.write("Total Files Processed: " + str(file_count) + "\n")
            file.write("---------------------\n")
            for key, value in statistics.items():
                file.write("File Name: " + key + "\n" + "-Censored Details: \n")
                for stat_key, stat_value in value.items():
                    file.write(f" -{stat_key.capitalize()}: {stat_value}\n")
                file.write("---------------------\n")


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
    input_files = glob.glob(args.input, recursive=True)
    file_statistics = {
        'names': 0,
        'addresses': 0,
        'dates': 0,
        'phone_numbers': 0,
    }
    file_count = 0
    nlp = load_spacy()
    for input_file in input_files:
        try:
            actual_file_name = os.path.basename(input_file)
            statistics[actual_file_name] = file_statistics.copy()
            process_file(input_file, args, nlp, actual_file_name)
            file_count += 1
        except Exception as e:
            print(f"Error processing {input_file}: {e}")
    write_data_to_stats(args.stats, file_count)


def process_file(input_file, args, nlp, actual_file_name):

    with open(input_file, 'r') as file:
        text_to_censor = file.read()
    res = censor_address(text_to_censor, actual_file_name)
    res = censor_name_and_date(res, nlp, actual_file_name)
    res = censor_phonenumbers(res, actual_file_name)
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    # output_file = os.path.join(args.output, os.path.splitext(os.path.basename(input_file))[0] + '.censored')
    output_file = os.path.join(args.output, os.path.basename(input_file) + '.censored')

    # Write the censored content to the output file
    with open(output_file, 'w') as file:
        file.write(res)


if __name__ == '__main__':
    main()