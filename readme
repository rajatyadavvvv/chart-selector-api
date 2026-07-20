# Chart Selector API

A containerized FastAPI service that automatically selects and renders the optimal chart type from tabular data. Upload a dataset, and the API applies rule-based logic to decide which of 11 chart types (line, scatter, bar, histogram, pie, box, violin, stacked bar, correlation heatmap, scatter matrix, and count bar) best represents the data — then renders it as a PNG with an auto-generated explanation of what the chart shows and what each axis/color means. The service is deployed on AWS using Docker, ECR, and ECS Fargate, with the build pipeline running through S3 and EC2.

## Architecture

![Architecture Diagram](docs/architecture-diagram.png)

The pipeline: code is zipped and pushed to S3 → an EC2 instance pulls it and builds the Docker image → the image is pushed to ECR → ECS Fargate is force-redeployed to pull the new image and serve it publicly.

## Decision Logic

![Decision Logic Flowchart](docs/decision-logic-flowchart.png)

The API inspects the uploaded dataset's column types (numeric, categorical, datetime) and column count to decide which chart type is most appropriate, then hands off to the renderer for that chart type.

## Tech Stack

- **Backend:** FastAPI
- **Data processing:** pandas, NumPy
- **Chart rendering:** matplotlib
- **Containerization:** Docker
- **Cloud infrastructure:** AWS (ECR, ECS Fargate, S3, IAM, EC2 for builds)

## Project Structure

```
chart-selector-api/
├── app/
│   ├── main.py
│   ├── data_loader.py
│   ├── chart_logic.py
│   └── chart_render.py
├── Dockerfile
├── requirements.txt
├── README.md
└── docs/
    ├── architecture-diagram.png
    ├── decision-logic-flowchart.png
    └── sample-charts/
```

## Running Locally

Clone the repo and set up a virtual environment:

```bash
git clone https://github.com/rajatyadavvvv/chart-selector-api.git
cd chart-selector-api
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Run the API with hot-reload:

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive FastAPI Swagger UI, or call it directly (see below).

## Example Request / Response

```bash
curl -X POST "http://127.0.0.1:8000/render-chart" \
  -F "file=@sample_data.csv" \
  -F "x=category" \
  -F "y=sales" \
  --output result.png
```

This returns a PNG chart like the ones below, each annotated with a caption explaining what's shown and what the axes/colors represent.

**Sample output:**

![Sample Bar Chart](docs/sample-charts/bar_example.png)

More examples across all 11 supported chart types are in [`docs/sample-charts/`](docs/sample-charts/).

## Deployment

The service was deployed on **AWS ECS Fargate**, built through a pipeline of:

1. Zip source → upload to **S3**
2. **EC2** build instance pulls the zip, builds the Docker image
3. Image pushed to **ECR**
4. **ECS Fargate** service force-redeployed to run the new image

IAM roles and security groups handle permissions and network access for the running task.

## Notes

- This project was built as a learning/portfolio exercise to practice end-to-end deployment (containerization → registry → orchestration) alongside data visualization logic.
- The AWS resources may not be live at all times to avoid ongoing costs — see the sections above for how to run it locally.
