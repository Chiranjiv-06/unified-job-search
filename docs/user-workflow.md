# End-to-End User Workflow Guide

## Workflow Steps

```
[1. Register / Login]
         │
         ▼
[2. Build Profile & Set Preferences]
         │
         ▼
[3. Upload PDF Resume -> Extract Skills/Experience]
         │
         ▼
[4. Discover / Add Job Postings]
         │
         ▼
[5. Run Verification & Risk Analysis]
         │
         ▼
[6. Review Explainable Match Score & Resume Suggestions]
         │
         ▼
[7. Apply on Official Portal & Log Application in System]
         │
         ▼
[8. Sync Recruitment Emails & Track Application Status]
         │
         ▼
[9. View Reminders for Follow-ups or Stalled Applications]
```

## Detailed Stage Descriptions

1. **Onboarding**: Candidate registers with valid email and password, receiving a JWT token.
2. **Profile Completion**: Candidate inputs education, career interests, target roles, and preferred locations.
3. **Resume Processing**: Candidate uploads a PDF resume. System extracts text, identifies skills, and asks for candidate confirmation.
4. **Job Acquisition**: Jobs are entered manually or imported via job link. Details such as required skills, experience, and location are stored.
5. **Verification Engine**: System verifies if the job URL aligns with official company career portals and checks for risk signals or duplicate listings.
6. **Matching Evaluation**: System scores the job against profile & resume, breaking down matching skills, missing skills, and eligibility flags.
7. **Application Submission**: Candidate clicks external link to apply directly on the legitimate portal, then marks status as `APPLIED` with application timestamp.
8. **Communication & Reminders**: System monitors response deadlines and surfaces reminders for timely follow-ups.
