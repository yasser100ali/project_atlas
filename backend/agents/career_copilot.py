from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain import hub
from .job_scraper import JobScraper
from .resume import ResumeGenerator
from dotenv import load_dotenv

load_dotenv()

class CareerAgent:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0, model="gpt-4.1")
        self.tools = self._load_tools()
        self.prompt = self._load_prompt()
        self.agent = self._create_agent()
        self.agent_executor = self._create_agent_executor()

    def _load_tools(self):
        return [JobScraper(), ResumeGenerator()]

    def _load_prompt(self):
        return hub.pull("hwchase17/react").partial(
            instructions="You are a helpful career assistant. Your goal is to help users with their job search. You have access to a job scraper and a resume generator. When a user asks for jobs, use the job scraper. When a user wants to create a resume, use the resume generator."
        )

    def _create_agent(self):
        return create_react_agent(self.llm, self.tools, self.prompt)

    def _create_agent_executor(self):
        return AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    def run(self, prompt: str):
        return self.agent_executor.invoke({"input": prompt})
