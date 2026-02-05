"""LangGraph workflow graph definition."""
from langgraph.graph import StateGraph, END

from src.workflow.state import WorkflowState
from src.workflow.nodes import create_pr_node, check_coverage_node, analyze_code_node, generate_tests_node, \
    clone_repository_node, should_generate_tests
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_workflow_graph() -> StateGraph:
    """
    Create the code coverage improvement workflow graph.

    Workflow:
    1. START → clone_repository
    2. clone_repository → check_coverage
    3. check_coverage → should_generate_tests (conditional)
    4. should_generate_tests → analyze_code (if coverage < threshold)
    5. should_generate_tests → END (if coverage >= threshold)
    6. analyze_code → generate_tests
    7. generate_tests → create_pr
    8. create_pr → END

    Returns:
        Compiled StateGraph
    """
    # Create workflow graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("clone_repository", clone_repository_node)
    workflow.add_node("check_coverage", check_coverage_node)
    workflow.add_node("analyze_code", analyze_code_node)
    workflow.add_node("generate_tests", generate_tests_node)
    workflow.add_node("create_pr", create_pr_node)

    # Set entry point
    workflow.set_entry_point("clone_repository")

    # Add edges
    workflow.add_edge("clone_repository", "check_coverage")

    # Conditional edge based on coverage threshold
    workflow.add_conditional_edges(
        "check_coverage",
        should_generate_tests,
        {
            "analyze_code": "analyze_code",
            "end": END,
        }
    )

    workflow.add_edge("analyze_code", "generate_tests")
    workflow.add_edge("generate_tests", "create_pr")
    workflow.add_edge("create_pr", END)

    # Compile the graph
    logger.info("Workflow graph created successfully")
    return workflow.compile()


# Create and export compiled workflow
compiled_workflow = create_workflow_graph()
