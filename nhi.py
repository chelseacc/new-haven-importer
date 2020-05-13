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

                # chapter_id = chapters_table.match('Name', row['Chapter']).get('id')  # record ID of New Haven Chapter
                # for k, v in row.items():
                #     v = v.strip()
                #     if not k.startswith(('day', 'restaurant', 'meals_number')):
                #         if k == 'Chapter':
                #             common[k] = [chapter_id or v]
                #         elif k == 'Recipient':
                #             if v == 'Yale New Haven Hospital - SRC':
                #                 v = 'Yale New Haven Hospital St Raphael Campus'
                #             common[k] = [recipients_table.match('Name', v).get('id')]
                #         else:
                #             common[k] = v
                #     # Monday
                #     elif k.endswith('one'):
                #         if row['day_one']:
                #             one['Delivery Scheduled'] = format_datetime_Y(row['day_one'])
                #             # if v == 'Roia Restaurant':
                #             #     row["restaurant_one"] = 'ROIA Restaurant'
                #             one['Restaurant'] = [restaurants_table.match('Name', row["restaurant_one"]).get('id')]
                #             one['Number of Meals'] = int(row["meals_number_one"])
                #     # Tuesday
                #     elif k.endswith('two'):
                #         if row['day_two']:
                #             two['Delivery Scheduled'] = format_datetime_Y(row['day_two'])
                #             # if v == 'Roia Restaurant':
                #             #     row["restaurant_two"] = 'ROIA Restaurant'
                #             two['Restaurant'] = [restaurants_table.match('Name', row["restaurant_two"]).get('id')]
                #             two['Number of Meals'] = int(row['meals_number_two'])
                    # # Wednesday
                    # elif k.endswith('three'):
                    #     three['Delivery Scheduled'] = format_datetime_y(
                    #         row['day_three'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                    #             "%I:%M%p"))
                    #     if v == 'Roia Restaurant':
                    #         row["restaurant_three"] = 'ROIA Restaurant'
                    #     three['Restaurant'] = [restaurants_table.match('Name', row["restaurant_three"]).get('id')]
                    #     three['Number of Meals'] = int(row['meals_number_three'])
                    # # Thursday
                    # elif k.endswith('four'):
                    #     four['Delivery Scheduled'] = format_datetime_y(
                    #         row['day_four'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                    #             "%I:%M%p"))
                    #     if v == 'Roia Restaurant':
                    #         row["restaurant_four"] = 'ROIA Restaurant'
                    #     four['Restaurant'] = [restaurants_table.match('Name', row["restaurant_four"]).get('id')]
                    #     four['Number of Meals'] = int(row['meals_number_four'])
                    # # Friday
                    # elif k.endswith('five'):
                    #     five['Delivery Scheduled'] = format_datetime_y(
                    #         row['day_five'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                    #             "%I:%M%p"))
                    #     if v == 'Roia Restaurant':
                    #         row["restaurant_five"] = 'ROIA Restaurant'
                    #     five['Restaurant'] = [restaurants_table.match('Name', row["restaurant_five"]).get('id')]
                    #     five['Number of Meals'] = int(row['meals_number_five'])
                    # # Saturday
                    # elif k.endswith('six'):
                    #     six['Delivery Scheduled'] = format_datetime_y(
                    #         row['day_six'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                    #             "%I:%M%p"))
                    #     if v == 'Roia Restaurant':
                    #         row["restaurant_six"] = 'ROIA Restaurant'
                    #     six['Restaurant'] = [restaurants_table.match('Name', row["restaurant_six"]).get('id')]
                    #     six['Number of Meals'] = int(row['meals_number_six'])
                    # # Sunday
                    # elif k.endswith('seven'):
                    #     seven['Delivery Scheduled'] = format_datetime_y(
                    #         row['day_seven'] + " " + datetime.strptime(row['day_one'], '%m/%d/%Y %I:%M%p').strftime(
                    #             "%I:%M%p"))
                    #     if v == 'Roia Restaurant':
                    #         row["restaurant_seven"] = 'ROIA Restaurant'
                    #     seven['Restaurant'] = [restaurants_table.match('Name', row["restaurant_seven"]).get('id')]
                    #     seven['Number of Meals'] = int(row['meals_number_seven'])

                # final_delivery_row_1 = {}
                # final_delivery_row_1.update(common)
                # final_delivery_row_1.update(one)
                # final_delivery_row_1.pop('empty')
                # deliveries_table.insert(final_delivery_row_1)  # insert delivery_row_1 to Airtable

                # final_delivery_row_2 = {}
                # final_delivery_row_2.update(common)
                # final_delivery_row_2.update(two)
                # final_delivery_row_2.pop('empty')
                # deliveries_table.insert(final_delivery_row_2)  # insert delivery_row_2 to Airtable

                # final_delivery_row_3 = {}
                # final_delivery_row_3.update(common)
                # final_delivery_row_3.update(three)
                # final_delivery_row_3.pop('empty')
                # deliveries_table.insert(final_delivery_row_3)  # insert delivery_row_3 to Airtable
                #
                # final_delivery_row_4 = {}
                # final_delivery_row_4.update(common)
                # final_delivery_row_4.update(four)
                # final_delivery_row_4.pop('empty')
                # deliveries_table.insert(final_delivery_row_4)  # insert delivery_row_4 to Airtable
                #
                # final_delivery_row_5 = {}
                # final_delivery_row_5.update(common)
                # final_delivery_row_5.update(five)
                # final_delivery_row_5.pop('empty')
                # deliveries_table.insert(final_delivery_row_5)  # insert delivery_row_5 to Airtable
                #
                # final_delivery_row_6 = {}
                # final_delivery_row_6.update(common)
                # final_delivery_row_6.update(six)
                # final_delivery_row_6.pop('empty')
                # deliveries_table.insert(final_delivery_row_6)  # insert delivery_row_6 to Airtable
                #
                # final_delivery_row_7 = {}
                # final_delivery_row_7.update(common)
                # final_delivery_row_7.update(seven)
                # final_delivery_row_7.pop('empty')
                # deliveries_table.insert(final_delivery_row_7)  # insert delivery_row_7 to Airtable

    except FatalError as err:
        print("\n\nFatal error, exiting: {}\n".format(err));
        sys.exit(1)


# Run this script
if __name__ == "__main__":
    exit(main())
