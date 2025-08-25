import os
import csv

def merge_csv_files(output_file="merged_output.csv"):
	csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
	merged_rows = []
	header_written = False
	with open(output_file, 'w', newline='', encoding='utf-8') as out_f:
		writer = None
		for file in csv_files:
			with open(file, 'r', encoding='utf-8') as in_f:
				reader = csv.reader(in_f)
				try:
					header = next(reader)
				except StopIteration:
					continue  # skip empty files
				header_with_file = ['SourceFile'] + header
				if not header_written:
					writer = csv.writer(out_f)
					writer.writerow(header_with_file)
					header_written = True
				for row in reader:
					writer.writerow([file] + row)

if __name__ == "__main__":
	merge_csv_files()
