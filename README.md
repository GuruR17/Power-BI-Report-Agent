# Power-BI-Report-Agent

An experimental Python toolkit that profiles tabular data (starting with Excel files) and
generates a Power BI report plan. The plan outlines recommended visuals and KPIs that can
be recreated inside Power BI Desktop or published automatically via the Power BI REST API.

## Features

- Load Excel workbooks and profile the selected sheet.
- Identify candidate numeric, categorical, and date fields.
- Generate a JSON report plan including suggested visuals and a narrative summary.
- Refine narratives and tailor visuals to business goals using an LLM (OpenAI compatible).
- Deploy datasets and reports directly to a Power BI workspace via the REST API.
- Command line interface for quick experimentation.

## Getting started

1. Install the package in a virtual environment:

   ```bash
   pip install -e .
   ```

2. Generate a plan from an Excel workbook:

   ```bash
   powerbi-agent path/to/workbook.xlsx --sheet "Sheet1" --output plan.json
   ```

3. Optionally include business goals so the LLM can adjust recommendations:

   ```bash
   export OPENAI_API_KEY=sk-...
   powerbi-agent workbook.xlsx --business-goals "Highlight year-over-year revenue growth"
   ```

4. Provide Power BI credentials to publish the generated plan straight to a workspace:

   ```bash
   export POWERBI_ACCESS_TOKEN="<aad access token>"
   powerbi-agent workbook.xlsx \
     --powerbi-group-id "<workspace-guid>" \
     --powerbi-report-name "Automated Report" \
     --powerbi-dataset-name "Automated Dataset"
   ```

   The CLI will create (or reuse) a push dataset with the detected schema and then call the
   Power BI REST API to create a report using the recommended visuals.

5. Open the resulting `plan.json` to inspect the recommended visuals or use the printed
   report ID to view the deployed report in Power BI.

## Configuration

- **LLM refinement** requires an OpenAI-compatible API key in `OPENAI_API_KEY`. Override
  the deployed model with `--llm-model` if needed, or disable refinement with `--no-llm`.
- **Power BI deployment** needs an Azure AD access token with permissions to create
  datasets and reports in the target workspace. Supply it with
  `--powerbi-access-token` (or `POWERBI_ACCESS_TOKEN`).

## Next steps

- Expand the `ExcelDataLoader` to support CSV and database sources.
- Add scheduling helpers to refresh push datasets with new data.
- Capture telemetry on deployed reports to continuously improve future recommendations.
