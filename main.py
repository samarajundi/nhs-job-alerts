import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import JOB_KEYWORDS, EXCLUDED_TERMS


SEEN_FILE = "jobs_seen.json"

BASE_URL = "https://apply.jobs.scot.nhs.uk"

LISTING_URL = (
    "https://apply.jobs.scot.nhs.uk/Home/_JobCard?Skip=0&what=Assistant%20Psychologist&Miles=&Salary=&LocationId=&Regions=&DivisionIds=&ClientCategory=&Departments=&SchoolLocationId=&JobLevels=&SchoolSubjectId=&JobTypeIds=&lat=&long=&EmploymentType=&postedDate="
)


def load_seen_jobs():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return []


def save_seen_jobs(jobs):
    with open(SEEN_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def get_page(url):
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    print(response.text[:500])

    return BeautifulSoup(
        response.text,
        "lxml"
    )


def find_job_links():

    soup = get_page(LISTING_URL)

    print("JOB CARD TEST:", "job-card" in str(soup))
    print("JOB DETAIL TEST:", "JobDetail" in str(soup))

    cards = soup.select(".job-card")

    print("Found job cards:", len(cards))

    links = []

    for card in cards:

        a = card.select_one("a[href*='JobDetail']")

        if a:

            href = a["href"]

            if href.startswith("/"):
                href = BASE_URL + href

            links.append(href)

    print("Collected links:", len(links))

    return links

def extract_job(url):

    soup = get_page(url)

    text = soup.get_text(
        " ",
        strip=True
    )

    title = soup.title.text if soup.title else "Unknown"

    return {
        "title": title,
        "url": url,
        "text": text.lower()
    }


def matches_job(job):

    text = (
        job["title"]
        + " "
        + job["text"]
    ).lower()


    keyword_match = any(
        keyword.lower() in text
        for keyword in JOB_KEYWORDS
    )


    if not keyword_match:
        return False


    excluded = any(
        term.lower() in text
        for term in EXCLUDED_TERMS
    )


    if excluded:
        return False


    return True


def send_email(jobs):

    if not jobs:
        return


    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]


    message = MIMEMultipart()

    message["From"] = sender
    message["To"] = sender
    message["Subject"] = (
        "New NHS Scotland Psychology Jobs"
    )


    body = (
        "New matching vacancies found:\n\n"
    )


    for job in jobs:

        body += (
            f"{job['title']}\n"
            f"{job['url']}\n\n"
        )


    message.attach(
        MIMEText(body, "plain")
    )


    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    ) as server:

        server.login(
            sender,
            password
        )

        server.send_message(
            message
        )


def main():

    print("Starting NHS job search...")


    seen = load_seen_jobs()


    links = find_job_links()

    print(
        f"Found {len(links)} job links"
    )


    matching_jobs = []


    for link in links:

        try:

            job = extract_job(link)


            if matches_job(job):

                if link not in seen:

                    matching_jobs.append(job)


        except Exception as e:

            print(
                f"Error processing {link}: {e}"
            )


    print(
        f"New matching jobs: {len(matching_jobs)}"
    )


    if matching_jobs:

        send_email(
            matching_jobs
        )

        seen.extend(
            job["url"]
            for job in matching_jobs
        )

        save_seen_jobs(
            seen
        )


if __name__ == "__main__":
    main()
