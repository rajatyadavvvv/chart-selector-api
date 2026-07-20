"""Chart Selector API — takes a JSON payload (columns + rows), returns a chart PNG."""

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from app.chart_logic import select_chart_type
from app.chart_render import ChartRenderError, render_chart
from app.data_loader import DataLoadError, DatasetPayload, load_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chart Selector API",
    description="Automatically selects and renders the best chart for a given JSON dataset.",
    version="3.0.0",
)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "chart-selector-api"}


@app.post(
    "/generate-chart",
    tags=["Charts"],
    responses={
        200: {"description": "Chart generated successfully", "content": {"image/png": {}}},
        400: {"description": "Invalid payload"},
        422: {"description": "Something went wrong while generating the chart"},
    },
)
async def generate_chart(payload: DatasetPayload):
    try:
        df = load_dataset(payload)
        decision = select_chart_type(df)
        buf = render_chart(df, decision)
    except DataLoadError as exc:
        logger.warning("Data load failed: %s", exc)
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except (ChartRenderError, ValueError) as exc:
        logger.error("Chart render failed: %s", exc)
        return JSONResponse(status_code=422, content={"error": str(exc)})

    return StreamingResponse(buf, media_type="image/png")