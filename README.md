### Tracking Famous People’s Residences from Wikipedia Dumps
## Overview

This project focuses on extracting and standardizing information about famous people’s residences over their lifetime.
Rather than web scraping live Wikipedia pages, it uses an offline Wikipedia dump (XML + bz2 format) to ensure efficiency, scalability, and respect for Wikipedia’s resources.

The pipeline is designed to:

Parse a massive XML dump.

Extract relevant data (primarily residence information).

Clean and structure the data.

Use tiers of LLMs to resolve ambiguous text into structured formats.

Simple requests → handled by a lightweight local LLM.

Complex requests → escalated to a more costly online LLM (e.g., Mistral, Gemini, GPT).

This system must scale to millions of API calls, requiring careful design in parallelization, data storage, and LLM selection.