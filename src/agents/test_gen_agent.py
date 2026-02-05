"""Test generation agent using LLM."""
from pathlib import Path
from typing import Dict, Any, List

from .base_agent import BaseAgent, AgentResult, AgentStatus, AgentError
from ..llm import LLMFactory


class TestGeneratorAgent(BaseAgent):
    """Agent for generating unit tests using LLM."""

    def __init__(
        self,
        llm_provider,
        test_framework: str = "pytest",
        test_directory: str = "tests",
        **kwargs: Any
    ):
        """
        Initialize test generator agent.

        Args:
            llm_provider: LLM provider instance
            test_framework: Testing framework to use
            test_directory: Directory for test files
        """
        super().__init__(**kwargs)
        self.llm = llm_provider
        self.test_framework = test_framework
        self.test_directory = test_directory

    def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Generate unit tests for identified candidates.

        Expected context keys:
            - test_candidates: List of functions to generate tests for
            - repo_path: Repository path
            - max_tests: Maximum number of tests to generate (optional)

        Returns:
            AgentResult with generated tests
        """
        self.validate_context(context, ["test_candidates", "repo_path"])
        
        test_candidates = context["test_candidates"]
        repo_path = Path(context["repo_path"])
        max_tests = context.get("max_tests", 10)

        # Limit number of tests to generate
        candidates_to_process = test_candidates[:max_tests]

        try:
            generated_tests = []
            test_files_created = []

            for candidate in candidates_to_process:
                self.logger.info(f"Generating test for: {candidate['name']}")
                
                # Read source code
                source_code = self._read_source_code(candidate)
                
                # Generate test code
                test_code = self._generate_test(candidate, source_code)
                
                # Write test file
                test_file_path = self._write_test_file(
                    repo_path,
                    candidate,
                    test_code
                )
                
                generated_tests.append({
                    "function": candidate["name"],
                    "test_file": str(test_file_path),
                    "success": True
                })
                test_files_created.append(str(test_file_path))

            self.logger.info(f"Generated {len(generated_tests)} test files")

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data={
                    "generated_tests": generated_tests,
                    "test_files": test_files_created,
                    "total_generated": len(generated_tests),
                },
                metadata={"framework": self.test_framework}
            )
        except Exception as e:
            self.logger.error(f"Test generation failed: {e}")
            raise AgentError(f"Test generation error: {e}")

    def _read_source_code(self, candidate: Dict[str, Any]) -> str:
        """Read source code for the function."""
        file_path = Path(candidate["file_path"])
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise AgentError(f"Failed to read source file: {e}")

    def _generate_test(self, candidate: Dict[str, Any], source_code: str) -> str:
        """Generate test code using LLM."""
        function_name = candidate.get("name")
        is_method = candidate.get("is_method", False)
        class_name = candidate.get("class_name")
        language = candidate.get("language", "python")

        # Create prompt
        prompt = self._create_test_prompt(
            function_name=function_name,
            source_code=source_code,
            is_method=is_method,
            class_name=class_name,
            docstring=candidate.get("docstring"),
            language=language
        )

        system_message = f"""You are an expert {language} developer writing unit tests using {self.test_framework}.
Generate comprehensive, well-structured unit tests that:
1. Cover different scenarios (happy path, edge cases, error cases)
2. Use appropriate fixtures and mocks where needed
3. Follow {self.test_framework} best practices
4. Include clear test names and docstrings
5. Are syntactically correct and ready to run

Output ONLY the test code, no explanations."""

        try:
            response = self.llm.generate(prompt, system_message=system_message)
            test_code = response.content

            # Clean up the code (remove markdown code blocks if present)
            test_code = self._clean_generated_code(test_code)
            
            return test_code
        except Exception as e:
            raise AgentError(f"LLM generation failed: {e}")

    def _create_test_prompt(
        self,
        function_name: str,
        source_code: str,
        is_method: bool,
        class_name: str = None,
        docstring: str = None,
        language: str = "python"
    ) -> str:
        """Create prompt for test generation."""
        target = f"{class_name}.{function_name}" if is_method else function_name
        prompt = f"""Generate unit tests for the following {language} code:

Target: {target}
Framework: {self.test_framework}

Source Code:
```{language}
{source_code}
```
"""
        if docstring:
            prompt += f"\nDocstring: {docstring}\n"
        prompt += f"""
Generate comprehensive unit tests that cover:
- Normal/happy path scenarios
- Edge cases
- Error handling
- Different input types/values

Output the complete test file content."""
        return prompt

    def _clean_generated_code(self, code: str) -> str:
        """Clean generated code (remove markdown wrappers, etc.)."""
        # Remove markdown code blocks
        if "```python" in code:
            code = code.split("```python", 1)[1]
            if "```" in code:
                code = code.rsplit("```", 1)[0]
        elif "```" in code:
            code = code.split("```", 1)[1]
            if "```" in code:
                code = code.rsplit("```", 1)[0]
        
        return code.strip()

    def _write_test_file(
        self,
        repo_path: Path,
        candidate: Dict[str, Any],
        test_code: str
    ) -> Path:
        """Write test code to file."""
        # Determine test file path
        source_file = Path(candidate["file_path"])
        relative_path = source_file.relative_to(repo_path / "src") if "src" in source_file.parts else source_file.relative_to(repo_path)
        
        # Create test file name
        test_file_name = f"test_{relative_path.stem}.py"
        test_file_path = repo_path / self.test_directory / relative_path.parent / test_file_name

        # Ensure directory exists
        test_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write test file
        try:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_code)
            
            self.logger.info(f"Created test file: {test_file_path}")
            return test_file_path
        except Exception as e:
            raise AgentError(f"Failed to write test file: {e}")
