from google.genai import types

# Tool Definition for Stage Transitions
ADVANCE_STAGE_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="advance_stage",
            description="Move the interview to the next logical stage based on conversation progress.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "next_node": types.Schema(
                        type="STRING",
                        enum=["EXPERIENCE", "DSA", "SQL", "REPORT"],
                        description="The target stage to transition to."
                    ),
                    "reason": types.Schema(
                        type="STRING",
                        description="Brief reason for the transition (e.g., 'Finished technical screening')."
                    )
                },
                required=["next_node"]
            )
        )
    ]
)

# Tool Definition for Code Submission
SUBMIT_CODE_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="submit_code",
            description="Call this when the candidate has finished their code or SQL solution and wants it graded.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "code": types.Schema(
                        type="STRING",
                        description="The full code or SQL query submitted by the candidate."
                    )
                },
                required=["code"]
            )
        )
    ]
)

ALL_TOOLS = [ADVANCE_STAGE_TOOL, SUBMIT_CODE_TOOL]
