#!/usr/bin/env python

################################################################
#
# nhi
#
# Imports a New Haven-style CSV and writes deliveries to the Backline
# Airtable base.
#
################################################################

import argparse  # pip install argparse
import csv  # core
import os  # core
import sys  # core
from airtable import Airtable  # pip install airtable-python-wrapper
from datetime import datetime  # core

# define a fatal error handler
class FatalError(Exception):
    pass

# Set up argparse
def init_argparse():
    parser = argparse.ArgumentParser(description='Imports a New Haven-style CSV and writes deliveries to Backline.')
    parser.add_argument('--csv', required=True, help='path to the CSV file to import')
    parser.add_argument('--verbose', action='store_true', help='print more information while processing')
    return parser


def format_datetime_Y(original_datetime):
    formatted = datetime.strptime(original_datetime, '%m/%d/%y %H:%M')
    converted = formatted.strftime("%Y-%m-%d" + "T" + "%H:%M:%S.%f")[:-3] + "Z"
    return converted


def fieldnames_parse(names):
    # Sample columns
    # ['Chapter', 'Recipient', 'Floor', 'Delivery Location', 'CONTACT PERSON', 'CONTACT NUMBER', 'Time', '5/27/20 Restaurants', '5/27/20 Meals']

    # check all our static fields are there
    proto_names = ['chapter', 'recipient', 'floor', 'delivery location', 'contact person', 'contact number', 'time']

    # set up case-insensitive compare
    names = [name.strip().lower() for name in names]
    for name in proto_names:
        if name not in names:
            raise FatalError("Required column '{}' not found.".format(name.title()))

    # find all the date fields and create columnsets
    dates_r = []
    dates_m = []
    for name in names:
        if name.endswith(' restaurants'):
            dates_r.append(name.replace(' restaurants', ''))
        if name.endswith(' meals'):
            dates_m.append(name.replace(' meals', ''))

    # confirm that all columnsets have both 'restaurants' and 'meals'
    dates_r.sort()
    dates_m.sort()
    if dates_r != dates_m:
            raise FatalError("Missing Restaurants or Meal column(s).")

    # confirm all dates parse properly
    iso_dates = {}
    for date in dates_r:
        iso_dates[date] = datetime.strptime(date, '%m/%d/%y').strftime('%Y-%m-%d')

    # return dict of {date:iso_date} representing columnsets
    return iso_dates

def main():
    try:
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

        # read CSV
        with open(args.csv, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            iso_dates = fieldnames_parse(reader.fieldnames)
            for row in reader:
                common = {
                    'Chapter': [chapters_table.match('Name', row['Chapter']).get('id')],
                    'Recipient': [recipients_table.match('Name', row['Recipient']).get('id')],
                    'Floor': row['Floor'],
                    'Delivery Location': [delivery_locations_table.match('Name', row['Delivery Location']).get('id')],
                    'Day of Hospital Contact': row['CONTACT PERSON'],
                    'Hospital Contact Phone': row['CONTACT NUMBER'],
                }
                clean_time = row['Time'].replace(" ", "")
                for date, iso_date in iso_dates.items():
                    print("{}, {}".format(date, iso_date))
                    print("{}T{}.000Z".format(iso_date, datetime.strptime(clean_time, '%I:%M%p').strftime("%H:%M:%S")))
                    # print( 'Delivery Scheduled': "{}T{}.000Z".format(iso_date, row('Time').strftime("%H:%M")) )
                    # print( "{}T{}.000Z".format(iso_date, row['Time']).strftime("%H:%M"))
                    print(row[date + ' Restaurants'])
                    print(row[date + ' Meals'])
                    if row[date + ' Restaurants'] and row[date + ' Meals']:
                        unique = {
                            'Delivery Scheduled': "{}T{}.000Z".format(iso_date, datetime.strptime(clean_time, '%I:%M%p').strftime("%H:%M:%S")),
                            'Restaurant': [restaurants_table.match('Name', row[date + ' Restaurants']).get('id')],
                            'Number of Meals': int(row[date + ' Meals'])
                        }
                        delivery_row = {}
                        delivery_row.update(common)
                        delivery_row.update(unique)
                        print(delivery_row)
                        deliveries_table.insert(delivery_row)
                    else:
                        raise FatalError("missing Restaurants/Meals on {} at {} for {}, floor: {}.".format(date, clean_time, row['Recipient'], row['Floor']))

                ## BOOKMARK ##
                raise FatalError("debug stop")

    except FatalError as err:
        print("\n\nFatal error, exiting: {}\n".format(err));
        sys.exit(1)


# Run this script
if __name__ == "__main__":
    exit(main())
