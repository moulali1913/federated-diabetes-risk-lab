# Federated Diabetes Risk Lab

Federated learning simulation for privacy-preserving diabetic risk prediction across hospitals.
Application project for 25PCCS202 - Python Programming (B.Tech CSE, CTMA, III Semester, 2026-2027).
Student: Shaik Mahammad Moulali (25BTRCM048). Guide: Dr. B. Narmada.

## Contents

| Folder | What it holds |
| --- | --- |
| `app/index.html` | The interactive simulation. Open it in any browser; no server or install needed. |
| `report/Application_Project_Report.pdf` | The 15-page project report with the cover page, certificate, abstract, chapters and references. |
| `report_source/` | `build.py` rebuilds the report PDF (needs Python, `playwright` with Chromium, and poppler's `pdftotext` and `pdfunite`). `logo.png` is the cover logo. |
| `experiments/` | `check.js` is the simulation code taken from the app. `run_experiments.js` reruns the multi-cohort experiments in Node.js (`node run_experiments.js`) and prints the numbers used in Chapter 6. |

## What the simulation does

- 3 to 10 virtual hospitals, each with synthetic patients based on the eight Pima diabetes features.
- Logistic regression trained with Federated Averaging (FedAvg); only 9 weights per hospital leave each site per round.
- Baselines: a model trained on pooled records and a model per hospital.
- Optional update clipping and Gaussian noise, to show the accuracy cost of privacy.
- Reports AUC and accuracy, per-hospital gains, and a patient risk calculator.

## Notes

- All patient data is synthetic. This is a teaching simulation, not a clinical tool, and the privacy noise has no formal (epsilon, delta) guarantee.
- The simulation is written in JavaScript so it runs in a browser. The course is a Python course, so a Python version would be a natural extension.
