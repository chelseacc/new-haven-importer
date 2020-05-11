#!/usr/bin/env python

################################################################
#
# nhi
#
# Imports a New Haven-style CSV and writes deliveries to the Backline
# Airtable base.
#
################################################################

import os  # core
import csv  # core
import argparse  # pip install argparse
from airtable import Airtable # pip install airtable-python-wrapper
from datetime import datetime

# Set up argparse
def init_argparse():
    parser = argparse.ArgumentParser(description='Imports a New Haven-style CSV and writes deliveries to Backline.')
    parser.add_argument('--csv', required=True, help='path to the CSV file to import')
    parser.add_argument('--verbose', action='store_true', help='print more information while processing')
    return parser


def format_datetime_Y(original_datetime):
    formatted = datetime.strptime(original_datetime, '%m/%d/%Y %I:%M%p')
    converted = formatted.strftime("%Y-%m-%d" + "T" + "%H:%M:%S.%f")[:-3] + "Z"
    return converted


def format_datetime_y(original_datetime):
    formatted = datetime.strptime(original_datetime, '%m/%d/%y %I:%M%p')
    converted = formatted.strftime("%Y-%m-%d" + "T" + "%H:%M:%S.%f")[:-3] + "Z"
    return converted


def main():
    # get auth keys from environment
    airtable_api_key = os.environ['AIRTABLE_API_KEY']
    airtable_base_backline = os.environ['AIRTABLE_BASE_BACKLINE']

    # get arguments
    argparser = init_argparse()
    args = argparser.parse_args()

    # set up Airtable connections
    deliveries_table = Airtable(airtable_base_backline, 'Deliveries', api_key=airtable_api_key)
    chapters_table = Airtable(airtable_base_backline, 'Chapters', api_key=airtable_api_key)
    delivery_locations_table = Airtable(airtable_base_backline, 'Delivery Locations', api_key=airtable_api_key)
    recipients_table = Airtable(airtable_base_backline, 'Recipients', api_key=airtable_api_key)
    restaurants_table = Airtable(airtable_base_backline, 'Restaurants', api_key=airtable_api_key)

    # Airtable column names
    airtable_fieldnames = ["Chapter", "Floor", "Day of Hospital Contact", "Hospital Contact Phone",
                           "Recipient", "Delivery Location", "empty", "day_one", "restaurant_one", "meals_number_one",
                           "day_two", "restaurant_two", "meals_number_two", "day_three", "restaurant_three",
                           "meals_number_three"]

    # read CSV
    with open(args.csv, newline='') as csvfile:
        next(csvfile, None)  # skip csv header
        reader = csv.DictReader(csvfile, fieldnames=airtable_fieldnames)
        for row in reader:
            common = {}
            one = {}
            two = {}
            three = {}
            chapter_id = chapters_table.match('Name', row['Chapter']).get('id')
            for k, v in row.items():
                v = v.strip()
                if not k.startswith(('day', 'restaurant', 'meals_number')):
                    if k == 'Chapter':
                        common[k] = [chapter_id or v]
                    elif k == 'Recipient':
                        if v == 'Yale New Haven Hospital - SRC':
                            v = 'Yale New Haven Hospital St Raphael Campus'
                        common[k] = [recipients_table.match('Name', v).get('id')]
                    elif k == 'Delivery Location':
                        common[k] = [delivery_locations_table.match('Name', v).get('id')]
                    else:
                        common[k] = v
                elif k.endswith('one'):
                    one['Delivery Scheduled'] = format_datetime_Y(row['day_one'])
                    if v == 'Roia Restaurant':
                        row["restaurant_one"] = 'ROIA Restaurant'
                    one['Restaurant'] = [restaurants_table.match('Name', row["restaurant_one"]).get('id')]
                    one['Number of Meals'] = int(row["meals_number_one"])
                elif k.endswith('two'):
                    two['Delivery Scheduled'] = format_datetime_y(
                        row['day_two'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                            "%I:%M%p"))
                    if v == 'Roia Restaurant':
                        row["restaurant_two"] = 'ROIA Restaurant'
                    two['Restaurant'] = [restaurants_table.match('Name', row["restaurant_two"]).get('id')]
                    two['Number of Meals'] = int(row['meals_number_two'])
                elif k.endswith('three'):
                    three['Delivery Scheduled'] = format_datetime_y(
                        row['day_three'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                            "%I:%M%p"))
                    if v == 'Roia Restaurant':
                        row["restaurant_three"] = 'ROIA Restaurant'
                    three['Restaurant'] = [restaurants_table.match('Name', row["restaurant_three"]).get('id')]
                    three['Number of Meals'] = int(row['meals_number_three'])

            final_delivery_row_1 = {}
            final_delivery_row_1.update(common)
            final_delivery_row_1.update(one)
            final_delivery_row_1.pop('empty')
            deliveries_table.insert(final_delivery_row_1)  # insert delivery_row_1 to Airtable

            final_delivery_row_2 = {}
            final_delivery_row_2.update(common)
            final_delivery_row_2.update(two)
            final_delivery_row_2.pop('empty')
            deliveries_table.insert(final_delivery_row_2)  # insert delivery_row_2 to Airtable

            final_delivery_row_3 = {}
            final_delivery_row_3.update(common)
            final_delivery_row_3.update(three)
            final_delivery_row_3.pop('empty')
            deliveries_table.insert(final_delivery_row_3)  # insert delivery_row_3 to Airtable


# Run this script
if __name__ == "__main__":
    exit(main())
