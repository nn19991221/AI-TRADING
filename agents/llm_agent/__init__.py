__all__ = ['LLMAgent', 'build_default_llm_agent']


def __getattr__(name):
    if name in {'LLMAgent', 'build_default_llm_agent'}:
        from .service import LLMAgent, build_default_llm_agent

        if name == 'LLMAgent':
            return LLMAgent
        return build_default_llm_agent
    raise AttributeError(name)
