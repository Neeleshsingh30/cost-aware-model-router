from prompt_builder import build_prompt


def test_classification():
    print("=" * 60)
    print("CLASSIFICATION")
    print("=" * 60)

    prompt = build_prompt(
        task_type="classification",
        input_text="I was charged twice for the same order.",
        categories=[
            "billing",
            "technical",
            "account",
            "sales",
        ],
    )

    print(prompt)


def test_extraction():
    print("=" * 60)
    print("EXTRACTION")
    print("=" * 60)

    prompt = build_prompt(
        task_type="extraction",
        input_text=(
            "Rahul Sharma ordered a Dell laptop for "
            "₹75,000 on 5 October 2026."
        ),
        fields=[
            "name",
            "product",
            "amount",
            "date",
        ],
    )

    print(prompt)


def test_summarisation():
    print("=" * 60)
    print("SUMMARISATION")
    print("=" * 60)

    prompt = build_prompt(
        task_type="summarisation",
        input_text=(
            "Machine learning is a branch of artificial "
            "intelligence that enables computers to learn "
            "patterns from data. It is commonly used for "
            "prediction, classification, recommendation, "
            "and automation. Machine learning systems "
            "improve their performance by learning from "
            "examples rather than following manually "
            "written rules for every situation."
        ),
    )

    print(prompt)


def test_qa():
    print("=" * 60)
    print("Q&A")
    print("=" * 60)

    prompt = build_prompt(
        task_type="qa",
        input_text=(
            "Python is a high-level programming language "
            "widely used in data science, machine learning, "
            "web development, and automation."
        ),
        question="What is Python commonly used for?",
    )

    print(prompt)


def main():
    test_classification()
    test_extraction()
    test_summarisation()
    test_qa()


if __name__ == "__main__":
    main()