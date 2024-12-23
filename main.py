import lxml
from bs4 import BeautifulSoup
import requests
import json
from selenium import webdriver
import time
from datetime import datetime
import pytz
from selenium.webdriver.chrome.service import Service
import pandas as pd
import schedule

url_multi_cinema = "https://multikino.lt/repertuaras/vilnius"
url_apollo_akrop = "https://www.apollokinas.lt/schedule?theatreAreaID=1019"
url_apollo_outlet = "https://www.apollokinas.lt/schedule?theatreAreaID=1024"
url_forum_cinema = "https://www.forumcinemas.lt"

lithuania_time = pytz.timezone("Europe/Vilnius")
lithuania_day = datetime.now(lithuania_time).strftime("%d")
words_to_remove = ["(dubbed)", "(dubliuotas)", "3D", "The", "the", "Part", "One"]
other_remove = [",", ":", "-", ".", " ", " "]

movies = []

headers = {
    "Accept" : "*/*",
    "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

service = Service(r"C:\Users\edvin\Desktop\Projects\Drivers\chromedriver-win64\chromedriver.exe")
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920x1080")
driver = webdriver.Chrome(service=service, options=options)

def get_multikino(url):
    print("Start parse Multikino")
    try:
        driver.get(url)
        time.sleep(5)
        # driver.save_screenshot("data/screenshot.png")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        src = driver.page_source
        # with open("data/multikino_scrap.html", "w") as file:
        #     file.write(src)

    except Exception as exe:
        print(exe)

    #
    # with open("data/multikino_scrap.html", "r") as file:
    #     src = file.read()

    soup = BeautifulSoup(src, "lxml")

    # div = soup.find_all("div", class_="filmlist__inner")
    div = soup.find_all("div", attrs={"data-hidden":"false"})
    seen_movies = set()
    seen_time = set()

    for item in div:
        # try:
        #     the_time = item.find(class_="date").text
        # except AttributeError:
        #     continue
        #
        # if lithuania_day in the_time:
        name = item.find("span", attrs={"rv-text" : "item.title"}).text
        for word in words_to_remove:
            if word in name:
                name = name.replace(word, "").strip().lower()
        for other in other_remove:
            if other in name:
                name = name.replace(other, "").strip()

        show_name = item.find("span", attrs={"rv-text" : "item.title"}).text
        href = item.find("a", class_="filmlist__info__more link link--light").get("href")
        full_href = "https://multikino.lt"+href
        about_film = item.find(attrs={"rv-text":"item.synopsis_short"}).text
        genre_elements = item.find("p", class_="film-details").find_all(attrs={"rv-text":"genre.name"})
        genres = [genre.text for genre in genre_elements]
        genres_str = ",".join(genres)
        age = item.find("span", attrs={"rv-text":"item.info_age"}).text
        start_time_elements = item.find("div", class_="day__section").find_all(attrs={"rv-datetime":"showing.date_time"})
        start_times = [start_time.text for start_time in start_time_elements]
        start_times_str = ", ".join(start_times)

        record = {
            "name" : name.lower(),
            "show_name" : show_name,
            "link" : full_href,
            "about" : about_film,
            "genre" : genres_str,
            "age" : age,
            "cinema" : "multikino",
            "time" : start_times_str
        }
        if (name, full_href) not in seen_movies:
            movies.append(record)
            seen_movies.add((name,full_href))
    print("Multikino parse end")

def get_apollo(url):
    print("Start pasrse Apollo")
    local_movies = []
    try:
        driver.get(url)
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        src = driver.page_source
        # with open(f"data/{file_name}_scrap.html", "w") as file:
        #     file.write(src)

    except Exception as exe:
        print(exe)

    #
    # with open(f"data/{file_name}_scrap.html", "r") as file:
    #     src = file.read()

    apollo_movies = {}

    soup = BeautifulSoup(src, "lxml")
    divs = soup.find_all("div", class_="schedule-card__inner")
    for item in divs:
        name_en = item.find("p", class_="schedule-card__secondary-title bold text-small").text
        name_lt = item.find("p", class_="schedule-card__title bold").text
        name = f"{name_lt} ({name_en})"
        for word in words_to_remove:
            name = name.replace(word, "").strip().lower()
        for other in other_remove:
            name = name.replace(other, "").strip()

        href = item.find("a").get("href")
        genre_elements = item.find_all("div", class_="schedule-card__genres bold text-small")
        genres = [genre.text.replace("\n", " ").strip() for genre in genre_elements]
        genres_str = ",".join(genres)
        time_start = item.find(class_="schedule-card__time bold").text
        age = item.find("div", class_="tag").text.strip()
        cinema = item.find("p", class_="schedule-card__cinema schedule-card__cinema--mobile").text

        print(f"Getting data for {name_en}")

        time.sleep(3)
        req_href = requests.get(href)
        src_href = req_href.text

        soup_href = BeautifulSoup(src_href, "lxml")
        about = soup_href.find("div", class_="media-chess__content").text.strip()

        if name in apollo_movies:
            apollo_movies[name]["time"].append(time_start)
        else:

            apollo_movies[name] = {
            "name" : name.lower(),
            "show_name" : name_en,
            "link" : href,
            "about" : about,
            "genre" : genres_str,
            "age" : age,
            "cinema" : cinema,
            "time" : [time_start]
            }

    for movie in apollo_movies.values():
        movie["time"] = ", ".join(movie["time"])
        local_movies.append(movie)

    movies.extend(local_movies)
    local_movies.clear()
    print("Apollo parse end")

def get_forumcinema(url):
    print("Start parse Forum Cinemas")
    time.sleep(3)
    req = requests.get(url, headers=headers)
    src = req.text

    # with open("data/forum_scrap.html", "w") as file:
    #     file.write(src)

    # with open("data/forum_scrap.html", "r") as file:
    #     src = file.read()

    forum_movies = {}

    soup = BeautifulSoup(src, "lxml")

    div = soup.find_all("div", class_="schedule-card schedule__item")

    for item in div:
        name_en = item.find("p", class_="schedule-card__secondary-title bold text-small").text.strip()
        name_lt = item.find("p", class_="schedule-card__title bold").text.strip()
        name = f"{name_lt} ({name_en})"
        for word in words_to_remove:
            name = name.replace(word, "").strip().lower()

        for other in other_remove:
            name = name.replace(other, "").strip()

        href = item.find("a").get("href")
        time_start = item.find("time", class_="schedule-card__time bold").text

        print(f"Getting data for {name_en}")

        time.sleep(3)
        req_href = requests.get(href)
        src_href = req_href.text
        soup_href = BeautifulSoup(src_href, "lxml")

        about = soup_href.find("div", class_="text").text.strip()
        genre = soup_href.find("p", class_="movie-details__value").text.strip()
        age = soup_href.find("div", class_="movie-details__tag").text.strip()

        if name in forum_movies:
            if time_start not in forum_movies[name]["time"]:
                forum_movies[name]["time"].append(time_start)
        else:
            forum_movies[name] = {
                "name" : name.lower(),
                "show_name" : name_en,
                "link" : href,
                "about" : about,
                "genre" : genre,
                "age" : age,
                "cinema" : "Forum_cinemas",
                "time" : [time_start]
            }

    for movie in forum_movies.values():
        movie["time"] = ", ".join(movie["time"])
        movies.append(movie)

# get_forumcinema(url_forum_cinema)
# df_exel = pd.read_excel("data/multicin.xlsx")
# df_movies = pd.DataFrame(movies)

def test_info():
    for index, row in df_movies.iterrows():
        if row["about"] == "-" or row["genre"] == "-" or row["age"] == "-":
            match = df_exel[df_exel["name"] == row["name"]]

            if not match.empty:
                df_movies.at[index,"about"] = match["about"].values[0] if row["about"] == "-" else row["about"]
                df_movies.at[index,"genre"] = match["genre"].values[0] if row["genre"] == "-" else row["genre"]
                df_movies.at[index, "age"] = match["age"].values[0] if row["age"] == "-" else row["age"]

    df_movies.to_excel("data/forum_cinemas.xlsx", index=False)

def load_info():
    get_multikino(url_multi_cinema)
    get_apollo(url_apollo_outlet)
    get_apollo(url_apollo_akrop)
    get_forumcinema(url_forum_cinema)

    df_movies = pd.DataFrame(movies)
    #
    # for index,row in df_movies.iterrows():
    #     if row["about"] == "-" or row["genre"] == "-" or row["age"] == "-":
    #         match = df_movies[df_movies["name"] == row["name"]]
    #
    #         if not match.empty:
    #             if row["about"] == "-":
    #                 df_movies.at[index, "about"] = match["about"].values[0] if match["about"].values[0] != "-" else row["about"]
    #             if row["genre"] == "-":
    #                 df_movies.at[index, "genre"] = match["genre"].values[0] if match["genre"].values[0] != "-" else row["genre"]
    #             if row["age"] == "-":
    #                 df_movies.at[index, "age"] = match["age"].values[0] if match["age"].values[0] != "-" else row["age"]

    df_movies.to_excel("data/all_data.xlsx")
    df_movies.to_csv("data/all_data.csv")

def run_scrapper():
    print(f"Scraping started at {datetime.now(pytz.timezone('Europe/Vilnius'))}")
    load_info()
    print(f"Scraping finished at {datetime.now(pytz.timezone('Europe/Vilnius'))}")

schedule.every().day.at("08:00").do(run_scrapper)
print("Scheduler started. Waiting for the next scheduled task...")

while True:
    schedule.run_pending()
    time.sleep(1)