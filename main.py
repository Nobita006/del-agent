from src.agent import ExcelAgent
import sys

def main():
    agent = ExcelAgent("data")
    print(agent.load_data())
    
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"\nQuestion: {question}")
        answer = agent.run(question)
        print(f"\nAnswer: {answer}")
    else:
        print("\nReady! Type a question (or 'exit'):")
        while True:
            q = input("> ")
            if q.lower() in ['exit', 'quit']:
                break
            answer = agent.run(q)
            print(f"Result: {answer}")

if __name__ == "__main__":
    main()
