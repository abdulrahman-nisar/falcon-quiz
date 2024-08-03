from flask import Flask, render_template, request
from ai71 import AI71
import re



def is_valid_input(topic):
    # Check if the input contains only alphabetic words with optional spaces
    if not re.match(r'^[a-zA-Z\s]+$', topic):
        return False

    # Check if the input contains at least one meaningful word and is not just a random string
    # Use a pattern to match sequences of letters with spaces, but ensure there are not too many consecutive letters
    meaningful_words = re.findall(r'[a-zA-Z]{2,}', topic)
    
    # Ensure that there is at least one meaningful word and the topic is not just a random string
    return len(meaningful_words) > 0 and not re.match(r'^[a-zA-Z]{10,}$', topic)


def is_number(str):
    try:
        int(str)
        return True
    except ValueError:
        return False


questions_store = []        #Store the list of all questions
answers = []                #Store the list of answers

app = Flask(__name__)
AI71_API_KEY = "ai71-api-b9c562fa-5175-459c-b812-ace5ca3044ee"

def generate_quiz(topic, num_questions):
    """Create the quiz"""
    
    #Declaring global variable
    global questions_store
    global answers
    
    
    questions = []  #store AI genrated text
    
    prompt = f"Generate {num_questions} quiz questions on the topic: {topic} with choices"
    question_text = ""
    
    #Getting quiz questions with choices
    for chunk in AI71(AI71_API_KEY).chat.completions.create(
        model="tiiuae/falcon-180b-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    ):
        if chunk.choices[0].delta.content:
            question_text += chunk.choices[0].delta.content
    
    print("DEBUG: Full response from AI71:")
    print(question_text)
    

    # Split the questions based on numbered pattern
    question_blocks = re.split(r'\d+\.', question_text)

    #Get answers from the AI
    answers_prompt = "Provide the correct answers for the following quiz questions on the topic: {topic}. Each answer should match the choices provided previously.\n"
    for question in question_blocks:
        answers_prompt += f"{question}\n"

    # Generate answers
    answers = []
    answer_text = ""

    for chunk in AI71(AI71_API_KEY).chat.completions.create(
        model="tiiuae/falcon-180b-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": answers_prompt},
        ],
        stream=True,
    ):
        if chunk.choices[0].delta.content:
            answer_text += chunk.choices[0].delta.content

    # Parse the generated answers into a list
    quiz_answers = answer_text.strip().split('\n')

    # Remove the first three characters from each answer
    quiz_answers = [s[3:] for s in quiz_answers]
    
    
    # Print or use the answers as needed
    print("\n")
    for answer in quiz_answers:
        print(f"{answer}")

    #parsing the AI text to seperate question and choices
    for block in question_blocks[1:]:  # skip the first empty split
        lines = block.strip().split('\n')   #Break each line into question and choices
        question_text = lines[0].strip()
        choices = []
        for line in lines[1:]:
            choices.append(line.strip())
        
        questions.append({"text": question_text, "choices": choices})   #stored whole quiz in questions in form of dictionary
    
    questions_store = [s["text"] for s in questions]    #Filling global variable
    answers = quiz_answers
   
    return questions

#Home page for  Again Quiz
@app.route('/')
def home():
    """Starting web page"""
    return render_template('index.html')


#Quiz generator page
@app.route('/generate', methods=['POST'])
def generate():
    """Create the quiz page"""
    global questions
    topic = request.form['topic']
    num_questions = request.form['num_questions']
    
    #Checking for avlid input
    if(is_valid_input(topic) == False):
        return render_template('index.html')
    
    questions = generate_quiz(topic, num_questions)
    
    return render_template('quiz.html', topic=topic, questions=questions)

@app.route('/rules')
def rules():
    return render_template('rules.html')


#Result page when user will submit the answer
@app.route('/submit', methods=['POST'])
def submit():
    """Show result"""
    global questions
    global answers

    # Clean user answers
    user_answers = {
        f"question_{index}": re.sub(r'^[a-dA-D]\.\s*', '', value) for index, (key, value) in enumerate(request.form.items())
    }
    

    score = 0  # User score
    total_score = len(questions)
    
    # Clean correct answers
    stripped_answers = [re.sub(r'^[a-dA-D]\.\s*', '', answer) for answer in answers]

    # Debugging information
    print(f"User Answers: {user_answers}")
    print(f"Stripped Answers: {stripped_answers}")

    # Calculate score
    for key, value in user_answers.items():
        question_index = int(key.split('_')[1])
        
        # Debugging information
        print(f"Processing Question Index: {question_index}")
        
        # Check if the question_index is within the valid range
        if question_index < len(stripped_answers):
            if value == stripped_answers[question_index]:
                score += 1
            print(f"User answer: {value}, Correct answer: {stripped_answers[question_index]}")
        else:
            print(f"Question index {question_index} is out of range for stripped_answers")

    # Prepare cleaned data for template
    cleaned_questions = [
        {
            'text': q['text'],
            'choices': [re.sub(r'^[a-dA-D]\.\s*', '', choice) for choice in q['choices']]
        }
        for q in questions
    ]

    # Debugging information
    print(f"Cleaned Questions: {cleaned_questions}")

    # Return result page with user's score and answers data
    return render_template(
        'result.html',
        score=score,
        total_score=total_score,
        questions=cleaned_questions,
        user_answers=user_answers,
        answers=stripped_answers
    )

if __name__ == '__main__':
    app.run(debug=True)
