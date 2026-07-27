import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import JOB_KEYWORDS, LOCATION, RADIUS_KM, EXCLUDED_TERMS


SEEN_FILE = "jobs_seen.json"


def load_seen_jobs():
    if not os.path.exists(SEEN_FILE):
        return []
    
    with open(SEEN_FILE, "r") as file:
        return json.load(file)


def save_seen_jobs(jobs):
    with open(SEEN_FILE, "w") as file:
        json.dump(jobs, file, indent=2)


def search_jobs():
    """
    Searches NHS Scotland Jobs.
    """

    url = "https://apply.jobs.scot.nhs.uk/"

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []

    for link in soup.find_all("a", href=True):

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        title_lower = title.lower()

        matches_keyword = any(
            keyword.lower() in title_lower
            for keyword in JOB_KEYWORDS
        )

        if matches_keyword:

            jobs.append({
                "title": title,
                "url": "https://apply.jobs.scot.nhs.uk" + link["href"]
            })

    return jobs


def filter_jobs(jobs):

    filtered = []

    for job in jobs:

        text = (
            job["title"]
            + " "
            + job["url"]
        ).lower()

        excluded = any(
            term.lower() in text
            for term in EXCLUDED_TERMS
        )

        if not excluded:
            filtered.append(job)

    return filtered


def send_email(jobs):

    if not jobs:
        return

    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]

    message = MIMEMultipart()

    message["From"] = sender
    message["To"] = sender
    message["Subject"] = "New NHS Scotland Psychology & Mental Health Jobs"

    body = "New matching jobs found:\n\n"

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

    seen = load_seen_jobs()

    jobs = search_jobs()

    jobs = filter_jobs(jobs)

    new_jobs = [
        job for job in jobs
        if job["url"] not in seen
    ]

    if new_jobs:

        send_email(new_jobs)

        seen.extend(
            job["url"]
            for job in new_jobs
        )

        save_seen_jobs(seen)


if __name__ == "__main__":
    main()
