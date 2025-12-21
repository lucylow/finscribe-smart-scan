"""
CAMEL ChatAgent setup for FinScribe invoice processing.
"""
import os
import logging
from typing import List, Optional

try:
    from camel.agents import ChatAgent
    from camel.messages import BaseMessage
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType, ModelType
    from camel.toolkits import FunctionTool
    CAMEL_AVAILABLE = True
except ImportError:
    CAMEL_AVAILABLE = False
    logging.warning("CAMEL-AI not available. Install with: pip install 'camel-ai[all]'")

from camel_tools import call_ocr_file_bytes, call_validator, llama_validate

logger = logging.getLogger(__name__)


def build_model():
    """
    Build model for CAMEL agent.
    Supports OpenAI, local vLLM, or dummy fallback.
    """
    if not CAMEL_AVAILABLE:
        raise ImportError("CAMEL-AI is not installed")
    
    # Check for OpenAI key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4o if hasattr(ModelType, "GPT_4o") else ModelType.GPT_4,
                model_config_dict={"temperature": 0.0}
            )
            logger.info("Using OpenAI model for CAMEL agent")
            return model
        except Exception as e:
            logger.warning(f"Failed to create OpenAI model: {e}, trying fallback")
    
    # Check for local vLLM endpoint
    vllm_url = os.getenv("VLLM_API_URL") or os.getenv("LLAMA_API_URL")
    if vllm_url:
        try:
            # Remove /v1/chat/completions if present, CAMEL will add it
            base_url = vllm_url.replace("/v1/chat/completions", "").rstrip("/")
            model = ModelFactory.create(
                model_platform=ModelPlatformType.VLLM,
                model_type=os.getenv("LLAMA_MODEL", "meta-llama/Llama-2-7b-chat-hf"),
                url=base_url,
                model_config_dict={"temperature": 0.0}
            )
            logger.info(f"Using vLLM model at {base_url} for CAMEL agent")
            return model
        except Exception as e:
            logger.warning(f"Failed to create vLLM model: {e}, trying dummy fallback")
    
    # Fallback to dummy model (will rely on tools)
    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DUMMY,
            model_type="dummy",
            model_config_dict={"temperature": 0.0}
        )
        logger.info("Using dummy model for CAMEL agent (tool-based processing)")
        return model
    except Exception as e:
        logger.error(f"Failed to create any model: {e}")
        raise


def make_agent():
    """
    Create and return a CAMEL ChatAgent with OCR and validation tools.
    """
    if not CAMEL_AVAILABLE:
        raise ImportError("CAMEL-AI is not installed. Install with: pip install 'camel-ai[all]'")
    
    model = build_model()
    
    # System message for the agent
    system_message = BaseMessage.make_assistant_message(
        role_name="FinScribe Orchestrator",
        content="""You orchestrate invoice processing workflows. You have access to tools for:
1. OCR processing: Extract text and structure from invoice images/documents
2. Validation: Correct and validate extracted JSON data

When given an invoice to process:
- First use the OCR tool to extract raw text and structure
- Then use the validation tool to correct and validate the JSON
- Return only the corrected, validated JSON structure

Always return valid JSON in your responses."""
    )
    
    # Wrap functions as CAMEL tools
    ocr_tool = FunctionTool(call_ocr_file_bytes, name="call_ocr_file_bytes")
    validator_tool = FunctionTool(call_validator, name="call_validator")
    
    # Optional: LLM validator tool if LLAMA_API_URL is set
    tools: List = [ocr_tool, validator_tool]
    
    if os.getenv("LLAMA_API_URL"):
        llama_validator_tool = FunctionTool(llama_validate, name="llama_validate")
        tools.append(llama_validator_tool)
    
    # Create agent
    agent = ChatAgent(
        system_message=system_message,
        tools=tools,
        model=model
    )
    
    logger.info(f"Created CAMEL ChatAgent with {len(tools)} tools")
    return agent


if __name__ == "__main__":
    # Test agent creation
    logging.basicConfig(level=logging.INFO)
    try:
        agent = make_agent()
        print("✓ CAMEL agent created successfully")
        
        # Test with a simple prompt
        test_prompt = BaseMessage.make_user_message(
            content="Process an invoice: extract text using OCR tool and validate the JSON structure."
        )
        
        print("\nTesting agent step...")
        resp = agent.step(test_prompt)
        print(f"Agent response: {resp.msgs[0].content if resp.msgs else 'No response'}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


