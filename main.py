import sqlite3
from urllib.parse import unquote
from collections import Counter, defaultdict
import math
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from dateutil import parser

# Specify the path to your SQLite database file
db_path = "path/to/tracking.sqlite"

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Function to format seconds into HH:MM:SS
def format_time(seconds):
    seconds = math.ceil(seconds)  # Round up to the nearest second
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    time_str = ""
    if hours > 0:
        time_str += f"{hours}h:"
    if minutes > 0 or hours > 0:  # Include minutes if there are hours
        time_str += f"{minutes}m:"
    time_str += f"{seconds}s"
    return time_str

# Function to filter rows by date range
def filter_by_date(rows, start_date=None, end_date=None):
    if start_date:
        start_date = parser.isoparse(start_date)
    if end_date:
        end_date = parser.isoparse(end_date)

    filtered_rows = []
    for row in rows:
        play_time = row[1]
        # Ensure start_date and end_date are offset-aware
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=play_time.tzinfo)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=play_time.tzinfo)
        if (not start_date or play_time >= start_date) and (not end_date or play_time <= end_date):
            filtered_rows.append(row)
    return filtered_rows

# Function to get the start and end dates for a given month and year
def get_month_date_range(year, month):
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
    return start_date.isoformat(), end_date.isoformat()

# Choose date range option
use_specific_date_range = False # Set to True to use specific date range, False to use month range

if use_specific_date_range:
    # Specific date range
    start_date = "2024-01-01T00:00:00"  # Example start date. Put "None" for all songs
    end_date = "2024-12-31T23:59:59"  # Example end date
else:
    # Month range
    start_date, end_date = get_month_date_range(2025, 1)  # Year, Month

# Convert start_date and end_date to datetime objects for date range calculation
start_date_dt = parser.isoparse(start_date)
end_date_dt = parser.isoparse(end_date)

# Calculate the date range using datetime objects
date_range = [start_date_dt + timedelta(days=i) for i in range((end_date_dt - start_date_dt).days + 1)]

# Query the database for the song plays
c.execute("""
SELECT songs.name, song_plays.play_time, song_plays.play_length, songs.length
FROM song_plays
JOIN songs ON song_plays.song_id = songs.id
ORDER BY song_plays.play_time
""")
rows = c.fetchall()

# Close the connection to the database
conn.close()

# Decode song names and parse play times
decoded_rows = [(unquote(row[0]), parser.isoparse(row[1]), row[2], row[3]) for row in rows]

# Filter rows by date range
filtered_rows = filter_by_date(decoded_rows, start_date, end_date)

# Calculate the number of plays based on 80% completion
play_counts = Counter()
cumulative_play_time = Counter()
total_cumulative_time = 0

# Choose whether to show 0, song_length only, or whatever % you want! Default: if play_length >= 0.8 * song length
play_mult = 0.8

for row in filtered_rows:
    song_name, play_time, play_length, song_length = row
    if play_length >= play_mult * song_length:
        play_counts[song_name] += 1
    cumulative_play_time[song_name] += play_length
    total_cumulative_time += play_length

# Set the number of top and cumulative plays for the console to output
top_plays = 10
top_cumu = 10

# Get the top n songs by number of plays
top_n_plays = play_counts.most_common(top_plays)

# Get the top n songs by cumulative play time
top_n_cumulative_time = cumulative_play_time.most_common(top_cumu)

# Get total plays for top n plays
total_plays = 0

# Print the results
print(f"Top {top_plays} Songs by Number of Plays:")
for song, count in top_n_plays:
    print(f"{song}: {count} plays")
    total_plays += count

print(f"\nNumber of Plays Total: {total_plays}")

print(f"\nTop {top_cumu} Songs by Cumulative Play Time:")
for song, total_time in top_n_cumulative_time:
    formatted_time = format_time(total_time)
    print(f"{song}: {formatted_time}")

# Print the total cumulative time of all songs listened to
formatted_total_cumulative_time = format_time(total_cumulative_time)
print(f"\nTotal Cumulative Time of All Songs Listened To: {formatted_total_cumulative_time}")

# -- OPTIONAL CHARTS --

# Extract play times for cumulative plays chart
play_times = [row[1] for row in filtered_rows]

# Calculate cumulative plays over time
cumulative_plays = list(range(1, len(play_times) + 1))

# Extract play counts per song per day
play_counts_per_day = defaultdict(lambda: defaultdict(int))
for row in filtered_rows:
    song_name, play_time, play_length, song_length = row
    play_counts_per_day[song_name][play_time.date()] += 1

# Calculate song discovery over time within the specified date range
first_play_times = defaultdict(lambda: None)
for row in filtered_rows:
    song_name, play_time = row[0], row[1]
    if first_play_times[song_name] is None or play_time < first_play_times[song_name]:
        first_play_times[song_name] = play_time

# Sort the songs by their first play time within the date range
sorted_first_play_times = sorted(first_play_times.items(), key=lambda x: x[1])

# Accumulate the count of discovered songs over time within the date range
discovery_dates = []
discovery_counts = []
count = 0
for song_name, play_time in sorted_first_play_times:
    count += 1
    discovery_dates.append(play_time)
    discovery_counts.append(count)

# Get list of all dates in the range
date_range = [start_date_dt + timedelta(days=i) for i in range((end_date_dt - start_date_dt).days + 1)]

# -- Separate Plots. Uncomment any plt.show() lines to display the data. --

# Plot cumulative plays and song discovery
plt.figure(figsize=(12, 8))
plt.plot(play_times, cumulative_plays, label='Cumulative Plays', linewidth=2)
plt.plot(discovery_dates, discovery_counts, label='Unique Songs Discovered', linewidth=2)
plt.xlabel('Date')
plt.ylabel('Count')
plt.title('Cumulative Song Plays and Unique Songs Discovered Over Time')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))  # Move legend to the side
plt.grid(True)
#plt.show()

# Plot daily listens for top n songs
plt.figure(figsize=(12, 8))

for song, counts in play_counts_per_day.items():
    if song in dict(top_n_plays):
        dates = sorted(counts.keys())
        listens = [counts[date] for date in dates]
        plt.plot(dates, listens, label=f'{song} Plays/Day')

plt.xlabel('Date')
plt.ylabel('Plays/Day')
plt.title('Daily Listens for Top Songs Over Time')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))  # Move legend to the side
plt.grid(True)
#plt.show()

# Plot cumulative plays over time for each top n song
plt.figure(figsize=(12, 8))

for song, counts in play_counts_per_day.items():
    if song in dict(top_n_plays):
        dates = sorted(counts.keys())
        cumulative_listens = np.cumsum([counts[date] for date in dates])
        plt.plot(dates, cumulative_listens, label=f'{song} Cumulative Plays')

plt.xlabel('Date')
plt.ylabel('Cumulative Plays')
plt.title('Cumulative Plays Over Time for Top Songs')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))  # Move legend to the side
plt.grid(True)
#plt.show()