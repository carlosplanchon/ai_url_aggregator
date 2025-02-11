#!/usr/bin/env python3

from openai import OpenAI

import os
import json

from pydantic import BaseModel
from pydantic import Field
from typing import List


import requests


PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


perplexity_client = OpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

openai_client = OpenAI(
    api_key=OPENAI_API_KEY
)


class UrlList(BaseModel):
    urls: List[str]


def query_models(query: str):
    perplexity_messages = [
        {
            "role": "user",
            "content": (
                query
            ),
        },
    ]

    # MODEL:
    # https://sonar.perplexity.ai/
    # demo chat completion without streaming.
    response = perplexity_client.chat.completions.create(
        # model="sonar-pro",
        # sonar-reasoning is the Deepseek without censorship hosted in the US.
        model="sonar-reasoning",
        messages=perplexity_messages,
    )
    # print(response)

    response_content: str = response.choices[0].message.content
    print(response_content)

    openai_messages = [
        {
            "role": "user",
            "content": (
                response_content
            ),
        },
    ]

    url_list_response = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=openai_messages,
        response_format=UrlList,
        temperature=0
    )

    url_list: list[str] = url_list_response.choices[0].message.parsed.urls

    return url_list


def keep_https(urls: list[str]) -> list[str]:
    # Create a dictionary to store the HTTPS version of each domain
    https_urls = {}

    for url in urls:
        try:
            # Extract the domain (without protocol)
            domain = url.split('//')[1]

            # If the URL is HTTPS, store it in the dictionary
            if url.startswith('https://'):
                https_urls[domain] = url

            # If the URL is HTTP and no HTTPS version has been stored yet,
            # store the HTTP version.
            elif url.startswith('http://') and domain not in https_urls:
                https_urls[domain] = url

        except Exception:
            ...

    # Return the values (URLs) from the dictionary
    return list(https_urls.values())


def execute_query_multiple_times(
    query: str,
    num_runs: int = 5
        ) -> list[str]:
    print("--- GET UNIQUE URLS ---")
    # Initialize an empty set to store unique URLs
    unique_urls = set()

    # Execute the function `num_runs` times
    for i in range(num_runs):
        print(f"i: {i}")
        # Get the URLs from the function
        urls: list[str] = query_models(query=query)

        urls = [url.rstrip("/") for url in urls]

        # Add the URLs to the set (duplicates will be automatically ignored)
        unique_urls.update(urls)

    # Convert the set back to a list if needed
    unique_urls_list = list(unique_urls)

    # Return the list of unique URLs
    return unique_urls_list


def check_urls_online(urls: list[str]) -> list[str]:
    online_urls = []

    for url in urls:
        try:
            # Set a timeout to avoid waiting too long.
            response = requests.head(url, timeout=5)
            if response.status_code in [200, 403]:
                online_urls.append(url)
            else:
                ...
        except requests.exceptions.RequestException:
            # Fallback to GET if HEAD fails
            try:
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 403]:
                    online_urls.append(url)
            except Exception:
                ...
    return online_urls


def search_for_web_urls(
    query: str,
    num_runs=5
        ) -> list[str]:
    query_response: list[str] = execute_query_multiple_times(
        query=query,
        num_runs=num_runs
    )
    prefer_https_urls = keep_https(
        urls=query_response
    )
    online_urls: list[str] = check_urls_online(
        urls=prefer_https_urls
    )

    return online_urls


class Website(BaseModel):
    name: str = Field(description="The name of the website.")
    url: str = Field(description="The url of the website.")


class WebsiteList(BaseModel):
    websites_list: list[Website] = Field(description="A short list.")


def get_top_relevant_websites(website_urls: list[str]) -> list[Website]:
    websites_list_dump = json.dumps(website_urls)

    # Get important websites with GPT.
    openai_messages = [
        {
            "role": "user",
            "content": (
                websites_list_dump
            ),
        },
        {
            "role": "system",
            "content": (
                "Select the most important websites from this JSON. Return a short list."
            ),
        }
    ]

    important_websites_fitered_by_gpt =\
        openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=openai_messages,
            response_format=WebsiteList,
            temperature=0
        )

    parsed_websites_list: list[Website] =\
        important_websites_fitered_by_gpt.choices[
            0].message.parsed.websites_list

    return parsed_websites_list
