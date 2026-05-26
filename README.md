# AI-Job-Matching

**app.py**
The actual web page. This is what opens in the browser when you run the app. It handles:

The form for individuals to fill in
The CSV upload for advisors
Displaying the results in a nice layout
The sidebar with the API key input

**matcher.py** 

This is where the matching logic lives:

Takes a person's profile and compares it against all the jobs
Ranks the jobs by how well they fit
Calls Claude to write the "why this fits you" explanation for each match
data/jobs.json
The job listings. Contains 15 EA-style jobs with details like title, org, salary, location, cause areas, and description. In a real version this would be replaced by live scraped data updated daily.

**requirements.txt**

A list of Python packages the app needs to run. When someone runs pip install -r requirements.txt it installs everything automatically.

**.env.example**

A template showing where to put the API key. Not strictly necessary for the demo since the key is entered in the sidebar, but good practice for developers.
