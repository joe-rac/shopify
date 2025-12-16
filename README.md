# RAC Shopify & Constant Contact Tools

This is a custom Python project developed and maintained by **Joe Moskowitz** to support the operations of the **Rockland Astronomy Club (RAC)**.

It provides tools to interact with both the **Shopify** e-commerce platform and **Constant Contact** mailing lists used by the club.

The project is **launched from the command line**, but most workflows immediately transition into a **Tkinter-based GUI** for interactive use. The central entry point is `rac_launcher.py`, which routes to the appropriate UI modules based on command-line arguments.

---

## 🚀 Features

- Pull and process Shopify orders via API
- Query Constant Contact to fetch contact lists (e.g., for door prize registration)
- Local-only, secure credential handling via `credentials.txt`
- GUI interfaces built with Tkinter for data review and manual actions
- Orchestrated launch of utilities through `rac_launcher.py`
- GraphQL API is the default mode for Shopify interactions

---

## ⚙️ API Usage Notes

- The project now uses **Shopify's GraphQL API** exclusively for both read and write operations.
- Older REST-based code is still present in the repo for reference but is deprecated and scheduled for removal.

---

## 📁 Project Structure

| File                      | Purpose                                                                 |
|---------------------------|-------------------------------------------------------------------------|
| `rac_launcher.py`         | **Main entry point**: Launches different RAC tasks like pulling orders or Constant Contact lists |
| `constant_contact.py`     | Logic to interact with Constant Contact's v3 API                        |
| `order_analysis.py`       | Filters and formats Shopify orders for RAC-specific use                 |
| `credentials.py`          | Centralized class for loading and distributing credentials              |
| `credentials.txt`         | **Not in repo. Local-only config file. See setup below.**               |
| `requirements.txt`        | Python packages required to run scripts                                |
| `.gitignore`              | Excludes sensitive and unnecessary files from repo (e.g., `credentials.txt`, IDE/project files) |

---

## 🔑 Credential Setup

You must create a local file named `credentials.txt` in the root directory of the project.  
This file is **intentionally excluded** from the repo via `.gitignore`.

### Example `credentials.txt`:
