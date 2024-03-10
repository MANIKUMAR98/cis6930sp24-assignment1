import copy

import spacy
import argparse
import glob
import os, re
from pathlib import Path
import pyap
import sys
import spacy.cli

from google.cloud import language_v1
from google.oauth2 import service_account


spacy.cli.download("en_core_web_md")
client = None
email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'


def load_spacy():
    nlp = spacy.load("en_core_web_md")
    return nlp


def load_google_nlp_cred():
    try:
        credentials = service_account.Credentials.from_service_account_file("./credentials/service_key.json")
        global client
        client = language_v1.LanguageServiceClient(credentials=credentials)
    except Exception as e:
        print("Exception occurred while extracting credentials ", e)


def censor_using_google_nlp(text, input_file_name, statistics, original_text):
    res = text
    try:
        document = language_v1.Document(content=original_text, type_=language_v1.Document.Type.PLAIN_TEXT)
        response = client.analyze_entities(document=document)
        for entity in response.entities:
            if entity.type_ == language_v1.Entity.Type.LOCATION:
                res = censor_text(res, entity.name, original_text)
                statistics[input_file_name]['addresses'] += 1
            elif entity.type_ == language_v1.Entity.Type.PHONE_NUMBER:
                res = censor_text(res, entity.name, original_text)
                statistics[input_file_name]['phone_numbers'] += 1
            elif entity.type_ == language_v1.Entity.Type.DATE:
                res = censor_text(res, entity.name, original_text)
                statistics[input_file_name]['dates'] += 1
            elif entity.type_ == language_v1.Entity.Type.PERSON:
                res = censor_text(res, entity.name, original_text)
                statistics[input_file_name]['names'] += 1
        return res
    except Exception as e:
        print("Exception occurred while censoring data using google nlp ", e)
        return res


def censor_using_spacy(text, nlp, input_file_name, statistics, original_text):
    censored_text = text
    try:
        doc = nlp(original_text)
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                censored_text = censor_text(censored_text, ent.text, original_text)
                statistics[input_file_name]['names'] += 1
            elif ent.label_ == 'DATE':
                censored_text = censor_text(censored_text, ent.text, original_text)
                statistics[input_file_name]['dates'] += 1
            elif ent.label_ in ['GPE', 'LOC']:
                censored_text = censor_text(censored_text, ent.text, original_text)
                statistics[input_file_name]['addresses'] += 1

        return censored_text
    except Exception as e:
        print("Exception occurred while censoring data using spacy ", e)
        return censored_text


def censor_address_using_pyap(text, input_file_name, statistics, original_text):
    censored_text = text
    try:
        addresses = pyap.parse(original_text, country='US')
        for address in addresses:
            address_str = str(address)
            censored_text = censor_text(censored_text, address_str, original_text)
            statistics[input_file_name]['addresses'] += 1
        return censored_text
    except Exception as e:
        print("Exception occurred while censoring addresses ", e)
        return censored_text


def write_data_to_stats(stats, file_count, statistics):
    if stats == "stderr":
        sys.stderr.write("Censoring Statistics:\n")
        sys.stderr.write("--------------------------\n")
        sys.stderr.write("Total Files Processed: " + str(file_count) + "\n")
        sys.stderr.write("---------------------\n")
        for key, value in statistics.items():
            sys.stderr.write("File Name: " + key + "\n" + "- Censored types and count: \n")
            for stat_key, stat_value in value.items():
                sys.stderr.write(f" - {stat_key.capitalize()}: {stat_value}\n")
            sys.stderr.write("--------------------------\n")
    elif stats == "stdout":
        sys.stdout.write("Censoring Statistics:\n")
        sys.stdout.write("--------------------------\n")
        sys.stdout.write("Total Files Processed: " + str(file_count) + "\n")
        sys.stdout.write("--------------------------\n")
        for key, value in statistics.items():
            sys.stdout.write("File Name: " + key + "\n" + "- Censored types and count: \n")
            for stat_key, stat_value in value.items():
                sys.stdout.write(f" - {stat_key.capitalize()}: {stat_value}\n")
            sys.stdout.write("--------------------------\n")
    else:
        with open(stats, 'w') as file:
            file.write("Censoring Statistics:\n")
            file.write("--------------------------\n")
            file.write("Total Files Processed: " + str(file_count) + "\n")
            file.write("--------------------------\n")
            for key, value in statistics.items():
                file.write("File Name: " + key + "\n" + "- Censored types and count: \n")
                for stat_key, stat_value in value.items():
                    file.write(f" - {stat_key.capitalize()}: {stat_value}\n")
                file.write("--------------------------\n")


def main():
    parser = argparse.ArgumentParser(description="Censor sensitive information in plain text documents.")
    parser.add_argument('--input', nargs='*', required=True, help='Input file pattern (e.g., "*.txt").')
    parser.add_argument('--names', action='store_true', help='Censor names.')
    parser.add_argument('--dates', action='store_true', help='Censor dates.')
    parser.add_argument('--phones', action='store_true', help='Censor phone numbers.')
    parser.add_argument('--address', action='store_true', help='Censor addresses.')
    parser.add_argument('--output', required=True, help='Output folder for censored files.')
    parser.add_argument('--stats', required=True, help='File or location to write statistics.')
    args = parser.parse_args()
    file_statistics = {
        'names': 0,
        'addresses': 0,
        'dates': 0,
        'phone_numbers': 0,
    }
    statistics = {}
    file_count = 0
    for pattern in args.input:
        input_files = glob.glob(pattern, recursive=True)
        nlp = load_spacy()
        load_google_nlp_cred()
        for input_file in input_files:
            if Path(input_file).exists() and input_file != "tests/test_file.txt":
                try:
                    actual_file_name = os.path.basename(input_file)
                    statistics[actual_file_name] = file_statistics.copy()
                    process_file(input_file, args, nlp, actual_file_name, statistics)
                    file_count += 1
                except Exception as e:
                    print(f"Error processing {input_file}: {e}")
                write_data_to_stats(args.stats, file_count, statistics)


def censor_email(res, actual_file_name, statistics, original_text):
    email_text = res
    try:
        email_list = []
        names_to_censor = []

        email_list = re.findall(email_pattern, email_text)

        for email in email_list:
            username, domain = email.split('@')
            name = re.sub(r'[._/-]', ' ', username)
            names_to_censor.extend(name.split(' '))

        names_string = ' '.join(names_to_censor)
        document = language_v1.Document(content=names_string, type_=language_v1.Document.Type.PLAIN_TEXT)
        response = client.analyze_entities(document=document)

        for entity in response.entities:
            if entity.type_ == language_v1.Entity.Type.PERSON:
                for value in names_to_censor:
                    email_text = censor_text(email_text, value, original_text)
                    statistics[actual_file_name]["names"] += 1
        return email_text
    except Exception as e:
        print("Exception occurred while censoring email", e)


def censor_text(text, replace_text, original_text):
    res = text
    try:
        index = original_text.find(replace_text)
        while index != -1:
            start_pos = index
            end_pos = start_pos + len(replace_text)
            censored_substring = ''.join('\u2588' if char != '\n' else char for char in original_text[start_pos:end_pos])
            res = res[:start_pos] + censored_substring + res[end_pos:]
            index = original_text.find(replace_text, end_pos)
        return res
    except Exception as e:
        print("Exception occurred while censoring text", e)


def process_file(input_file, args, nlp, actual_file_name, statistics):
    try:
        with open(input_file, 'r') as file:
            text_to_censor = file.read()
        original_text = copy.deepcopy(text_to_censor)
        res = censor_address_using_pyap(text_to_censor, actual_file_name, statistics, original_text)
        res = censor_email(res, actual_file_name, statistics, original_text)
        res = censor_using_google_nlp(res, actual_file_name, statistics, original_text)
        res = censor_using_spacy(res, nlp, actual_file_name, statistics, original_text)
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        output_file = os.path.join(args.output, os.path.basename(input_file) + '.censored')

        with open(output_file, 'w') as file:
            file.write(res)
    except Exception as e:
        print("Exception occurred while processing file ", e)


if __name__ == '__main__':
    main()
