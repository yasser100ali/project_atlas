import asyncio
import random
from agents import Agent, ItemHelpers, Runner, function_tool
from dotenv import load_dotenv

load_dotenv() 


@function_tool
def how_many_jokes() -> int:
    return random.randint(1, 10)

@function_tool
def count_chars(sentence: str) -> int:
    return len(sentence)

async def main():
    agent = Agent(
        name="Joker",
        instructions="For jokes, First call the `how_many_jokes` tool, then tell that many jokes. If the user asks to count chars in sentence then use 'count_chars'",
        tools=[how_many_jokes, count_chars],
        model="gpt-4.1"
    )

    result = Runner.run_streamed(
        agent,
        input="Dark humored jokes please. Also count how many characters are in all these these sentences. Count how many chars in each joke and only return those that are less than 80.",
    )


    print("=== Run starting ===")

    async for event in result.stream_events():
        # We'll ignore the raw responses event deltas
        if event.type == "raw_response_event":
            continue
        # When the agent updates, print that
        elif event.type == "agent_updated_stream_event":
            print(f"Agent updated: {event.new_agent.name}")
            continue
        # When items are generated, print them
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                print("-- Tool was called")
            elif event.item.type == "tool_call_output_item":
                print(f"-- Tool output: {event.item.output}")
            elif event.item.type == "message_output_item":
                print(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
            else:
                pass  # Ignore other event types

    print("=== Run complete ===")


if __name__ == "__main__":
    asyncio.run(main())