# API Key
#	uAliGOLMbJAzNnUqJdKovrjEI
# API Secret Key
#	4ISolaozxIYV0u7r3fB8YiM0vIyMpfngNcpvSqXztRHAqlXSIN
# Bearer Token
#	AAAAAAAAAAAAAAAAAAAAAFDnOwEAAAAAuVpF5lkNhm9twDEJDN6fI2t2q8o%3Dsnp2jKHOcnvxyModNwCiz78baDnufScYjfpQkbWkNBb1seoTmK


import os
import nba_scraper.nba_scraper as ns
import csv
import json.decoder
from functools import wraps
import errno
import signal

## directory to save game data to
dir = os.getcwd()
gamesDir = "Games"

################################################################################
################################################################################
################################################################################
## Timeout Handler
## https://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish

class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
################################################################################
################################################################################
################################################################################

## Dictionary of teams and their 3x2 stats {hits, games played}
threeByDict = {
	"ATL": [0, 0], "BKN": [0, 0], "BOS": [0, 0], "CHA": [0, 0], "CHI": [0, 0], "CLE": [0, 0],
	"DAL": [0, 0], "DEN": [0, 0], "DET": [0, 0], "GSW": [0, 0], "HOU": [0, 0], "IND": [0, 0],
	"LAC": [0, 0], "LAL": [0, 0], "MEM": [0, 0], "MIA": [0, 0], "MIL": [0, 0], "MIN": [0, 0],
	"NOP": [0, 0], "NYK": [0, 0], "OKC": [0, 0], "ORL": [0, 0], "PHI": [0, 0], "PHX": [0, 0],
	"POR": [0, 0], "SAC": [0, 0], "SAS": [0, 0], "TOR": [0, 0], "UTA": [0, 0], "WAS": [0, 0],
}

## Checks whether the 3x2 hit for a specified game
@timeout(10)
def didHit(game_id):
	## If csv file already exists in the directory, skip over the scrape
	## This is so we don't waste time sending requests
	## Else, scrape that game's data
	if (os.path.exists(f"{dir}/{gamesDir}/{str(game_id)}.csv")):
		print(f"Scraping game id: 00{game_id}")
	else:
		## Scrapes a game's data, and saves the data to a csv in dir
		ns.scrape_game([game_id], data_format='csv', data_dir=gamesDir)

	## This will create a temporary csv_file to read data from
	with open(f"{dir}/{gamesDir}/{str(game_id)}.csv") as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		line_count = 0
		threes_made = 0
		threeBy_made = 0
		## Loop through each row in the csv
		for row in csv_reader:
			## If on the first line, skip (column headers)
			if (line_count == 0):
				## move to next line
				line_count += 1
			else:
				## row[4]:	period
				## row[43]: shot_made
				## row[48]: is_three
				## If a three is made in the first quarter
				if (row[4] == '1' and row[43] == '1.0' and row[48] == '1'):
					## If time left in quarter >= 9:00
					if (int(row[6][:(row[6].index(':'))]) >= 9):
						## Count a 3x2 bucket
						threeBy_made += 1
					## Count a 3 pointer
					threes_made += 1
				## move to next line
				line_count += 1

		## Increment game count for each team
		threeByDict[row[34]][1] += 1
		threeByDict[row[35]][1] += 1

		## If the 3x2 hit, add count to the teams
		if (threeBy_made >= 2):
			threeByDict[row[34]][0] += 1
			threeByDict[row[35]][0] += 1

	print(f"\t{game_id}: There were {threes_made} threes made in the first quarter, with {threeBy_made} made in the first 3 minutes.")

	## Did it hit??
	if (threeBy_made >= 2):
		## Yes :D $$$
		print(f"\t{game_id}: CASHED!\n")
		return True
	## No :( XXX
	print(f"\t{game_id}: down bad...\n")
	return False

## Retrieves data from a range of games
## 2020-21 Season: Starts at 22000001
def retrieveData(gameID_start, gameID_end):
	## Count for number of games scanned
	count = 0
	## Count for number of games corrupted
	corrupted = 0
	## Count for number of games corrupted in a row
	consecCorrupted = 0
	for game_id in range(gameID_start, gameID_end):
		count += 1
		try:
			## Check if the 3x2 hit for this game
			didHit(game_id)
			corrupted += consecCorrupted
			## Reset number of consecutive corrupted games
			consecCorrupted = 0
		## This may happen if the range is out of bounds
		except json.decoder.JSONDecodeError:
			print("\tJSON Decoder Error - index must be out of range...exiting\n")
			break
		## This may happen if there is no data for the game
		except IndexError:
			print("\tGame corrupted...continuing\n")
			consecCorrupted += 1
			## If there are 3 corrupted games in a row
			## We are probably at the end of existing games if True
			if (consecCorrupted == 3):
				count -= 3
				print("\t3 consecutive games corrupted...exiting\n")
				break
		## This may happen if the request took too long
		except TimeoutError:
			print("\tRequest timed out...continuing\n")
			consecCorrupted += 1
			## If there are 3 corrupted games in a row
			## We are probably at the end of existing games if True
			if (consecCorrupted == 3):
				count -= 3
				print("\t3 consecutive games corrupted...exiting")
				break

	print(f"\n\nFinished!\n\n{corrupted} out of {count} games were corrupted. ({(float(corrupted)/float(count)):.3f}%)\n")

	for team, count in sorted(threeByDict.items(), key=lambda x: (x[1][0]/x[1][1]), reverse=True):
		print(f"{team} : {(100*count[0]/count[1]):.3f}% ({count[0]}/{count[1]})")

retrieveData(22000001, 22001000)
