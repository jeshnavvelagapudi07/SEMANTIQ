"""
Evaluation API Router
Runs automated benchmarks on golden test cases and returns measured accuracy and security metrics.
"""
from fastapi import APIRouter
from app.models.schemas import EvaluationReport
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])


@router.get("", response_model=EvaluationReport)
async def get_evaluation_report():
    """
    Executes live benchmark suite across golden queries and returns real measured metrics.
    """
    report = await evaluation_service.run_evaluation()
    return report


@router.post("/run", response_model=EvaluationReport)
async def trigger_evaluation_run():
    """
    Forces a fresh execution of the evaluation suite.
    """
    report = await evaluation_service.run_evaluation()
    return report
