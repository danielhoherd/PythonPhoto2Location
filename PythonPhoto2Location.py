#!/usr/bin/env python3
import calendar
import datetime
import os
import tkinter
import webbrowser
from decimal import Decimal
from pathlib import Path
from sys import exit
from sys import version_info
from threading import Thread
from typing import Any
from typing import Optional

import country_converter as coco
import pandas as pd
import reverse_geocoder as rg
from gmplot import gmplot
from PIL import Image as PilImage  # 'Image' conflicts with tkinger.Image
from PIL.ExifTags import GPSTAGS
from PIL.ExifTags import TAGS

if version_info < (3, 6):
    exit("This tool requires py36+")

google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
if not google_maps_api_key:
    exit("you must export your Google Maps API key as GOOGLE_MAPS_API_KEY")

# Initialize the main window and all components
window = tkinter.Tk()
window.minsize(500, 500)
window.title("Photo To Location")
window.wm_iconbitmap("window_icon.ico")
entryText = tkinter.StringVar()
textbox = tkinter.Entry(window, width=75, textvariable=entryText)
textbox.place(x=10, y=20)
link2 = tkinter.Label(window, text="", fg="blue", cursor="hand2")
link2.place(x=160, y=90)
link1 = tkinter.Label(window, text="", fg="blue", cursor="hand2")
link1.place(x=270, y=90)
label = tkinter.Label(window, text="")
label.place(x=10, y=80)
label2 = tkinter.Label(window, text="")
label2.place(x=10, y=96)
status_message = tkinter.StringVar()
status = tkinter.Label(window, textvariable=status_message, bd=1, relief=tkinter.SUNKEN, anchor=tkinter.W)
status.pack(side=tkinter.BOTTOM, fill=tkinter.X)
text = tkinter.Text(window, height=22, width=59)
text.place(x=10, y=120)
cpt = 0


def get_labeled_exif(exif):
    labeled = {}
    for (key, val) in exif.items():
        labeled[TAGS.get(key)] = val
    return labeled


def get_exif(filename):
    image: Optional[Any] = PilImage.open(filename)
    image.verify()
    return image._getexif()


def get_geotagging(exif):
    if not exif:
        raise ValueError("No EXIF metadata found")
    geo_tagging = {}
    for (idx, tag) in TAGS.items():
        if tag == "GPSInfo":
            if idx not in exif:
                # raise ValueError("No EXIF geo_tagging found")
                exit("No coords found in EXIF data")
            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geo_tagging[val] = exif[idx][key]
    return geo_tagging


def get_decimal_from_dms(dms, ref):
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0
    if ref in ["S", "W"]:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds
    return round(degrees + minutes + seconds, 5)


def get_coordinates(geotags):
    lat = get_decimal_from_dms(geotags["GPSLatitude"], geotags["GPSLatitudeRef"])
    lon = get_decimal_from_dms(geotags["GPSLongitude"], geotags["GPSLongitudeRef"])
    return lat, lon


def date_time_converter(date_time):
    format = "%Y:%m:%d"  # The format
    datetime_str = datetime.datetime.strptime(date_time, format)
    return datetime_str


# Function to find the screen dimensions, calculate the center and set geometry
def center(win):
    win.update_idletasks()
    width = win.winfo_width()
    height = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


def ask_quit():
    window.destroy()
    exit()


def on_closing():
    root = tkinter.Tk()
    root.destroy()
    window.destroy()
    exit()


def open_file_dialog():
    global cpt
    root = tkinter.Tk()
    root.withdraw()
    folder_selected = tkinter.filedialog.askdirectory()
    entryText.set(folder_selected)
    print("Directory to Process: " + folder_selected)
    cpt = sum([len(files) for r, d, files in os.walk(folder_selected)])
    print("Number of Files using listdir method#1 :", cpt)


def open_excel(event):
    os.startfile("results.xlsx")


def percentage(part, whole):
    return round(100 * float(part) / float(whole), 2)


def start_thread():
    Thread(target=process, daemon=True).start()


def callback(url):
    webbrowser.open_new(url)


# Define button press function
def process():
    print("Starting to Parse Image Exif Information")
    global cpt
    global status_message
    status_message.set("")
    link1.config(text="")
    link2.config(text="")
    text.delete("1.0", tkinter.END)
    status.config(text="")
    count = 0
    path = Path(entryText.get())
    files = [f for f in path.glob("**/*.jpg")]
    visited_cities = []
    visited_cities_clean = []
    visited_coordinates_lat = []
    visited_coordinates_lon = []
    visited_coordinates = []
    months = []
    years = []
    cities = []
    countries = []

    for f in files:
        print(f"working with file: {f}")
        count = count + 1
        print(f"working with file #{count}: {f}")
        if count % 10 == 0:
            status_message.set("Processing Image: " + str(count) + " of " + str(cpt) + " (" + str(percentage(count, cpt)) + "%)")
        try:
            exif = get_exif(f.as_posix())
            geo_tags = get_geotagging(exif)
            coordinates = get_coordinates(geo_tags)
            lat = float(Decimal(coordinates[0]).quantize(Decimal(10) ** -3))
            lon = float(Decimal(coordinates[1]).quantize(Decimal(10) ** -3))
            results = rg.search(coordinates, mode=1)
            city = results[0].get("name") + ", "
            state = results[0].get("admin1") + ", "
            country = results[0].get("cc")
            cc = coco.CountryConverter(include_obsolete=True)
            country = cc.convert(country, to="name_short")

            try:
                datum = geo_tags["GPSDateStamp"]  # TODO: handle when this is missing
                year = str(date_time_converter(datum).year)
                month = str(date_time_converter(datum).month)
            except:
                raise
                try:
                    datum = str(PilImage.open(f)._getexif()[36867]).split(" ", 1)[0]
                    year = str(date_time_converter(datum).year)
                    month = str(date_time_converter(datum).month)
                except:
                    year = "1970"
                    month = "00"

            year = f"{year:02}"
            month = f"{month:02}"

            # print(f)
            if year != "1970" and month != "00":
                visited_cities.append(year + ":" + month + " | " + city + state + country)

            # print("Location:" + city + state + country + " | " + f)
            for word in visited_cities:
                if word not in visited_cities_clean:
                    visited_cities_clean.append(word)
                    label.config(text=f"Processing Coordinates: {coordinates}")
                    label2.config(text="Successfully Resolved: " + city + state + country)
                    if lat != 0.000 and lon != 0.000:
                        visited_coordinates_lat.append(lat)
                        visited_coordinates_lon.append(lon)
                        visited_coordinates.append(city + country + "|" + str(lat) + "|" + str(lon) + "|" + year + ":" + month)
                        months.append(month)
                        years.append(year)
                        cities.append(results[0].get("name"))
                        countries.append(country)
                        text.insert(tkinter.END, year + "/" + month + " - " + city + country + "\n")
                        text.see("end")
        except:
            exit(f"GPS Data Missing in {f}")

    status_message.set("Processed: " + str(count) + " images")
    label.config(text="")
    label2.config(text="")
    print("--- GOOGLE MAP Generated ---")
    google_map = gmplot.GoogleMapPlotter(0, 0, 2)
    google_map.coloricon = "http://www.googlemapsmarkers.com/v1/%s/"
    google_map.apikey = google_maps_api_key
    google_map.heatmap(visited_coordinates_lat, visited_coordinates_lon)
    google_map.plot(visited_coordinates_lat, visited_coordinates_lon, c="#046CC6", edge_width=1.0)

    # ADD MARKERS
    for word in visited_coordinates:
        title = word.split("|")[0]
        lati = word.split("|")[1]
        long = word.split("|")[2]
        date = word.split("|")[3]
        date = date.split(":")
        month_word = calendar.month_name[int(date[1])]
        google_map.marker(
            float(lati), float(long), "cornflowerblue", title=str(title) + " (" + str(date[0]) + " " + str(month_word) + ")"
        )

    google_map.draw("result.html")

    link1.config(text="Open Map")
    link1.bind("<Button-1>", lambda e: callback("result.html"))

    link2.config(text="Open Excel")
    link2.bind("<Button-1>", open_excel)

    df = pd.DataFrame(
        {
            "Month": months,
            "Year": years,
            "City": cities,
            "Country": countries,
            "Lat.": visited_coordinates_lat,
            "Long.": visited_coordinates_lon,
        }
    )
    writer = pd.ExcelWriter("results.xlsx", engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1", startrow=1, header=False)
    workbook = writer.book
    worksheet = writer.sheets["Sheet1"]

    header_format = workbook.add_format({"bold": True, "text_wrap": False, "valign": "top", "fg_color": "#D7E4BC", "border": 1})

    # Write the column headers with the defined format.
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num + 1, value, header_format)

    # Close the Pandas Excel writer and output the Excel file.
    df.sort_values(["Month", "Year"], ascending=[True, True])
    writer.save()
    text.insert(tkinter.END, "\n")
    text.insert(tkinter.END, "---------------END---------------\n")
    text.insert(tkinter.END, "\n")
    text.see("end")
    print("-------------END------------")


# Place 'Change Label' button on the window
button = tkinter.Button(window, text="...", command=open_file_dialog)
button.place(x=470, y=17)
process_button = tkinter.Button(window, text="Process Images", command=start_thread)
process_button.place(x=10, y=50)

# Center Window on Screen
center(window)

# close the program and tkinter window on exit
window.protocol("WM_DELETE_WINDOW", ask_quit)
# Show new window
window.mainloop()
