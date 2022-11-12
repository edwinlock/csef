from importlib.util import LazyLoader
from tokenize import Number
from wsgiref import validate
from xmlrpc.client import Boolean
from flask_wtf import FlaskForm
from sqlalchemy import Integer
from flask import Markup

from wtforms import StringField, PasswordField, BooleanField, IntegerField, \
    SubmitField, TextAreaField, FormField, BooleanField, RadioField, DecimalField, EmailField, SelectField, DateTimeField, DateField, Label, Field
from flask_wtf.file import FileAllowed, FileField
from wtforms.validators import ValidationError, DataRequired, InputRequired, \
                               Email, EqualTo, Length, URL, Optional, NumberRange

from wtforms.widgets import RangeInput, RadioInput
from flask_babel import gettext, lazy_gettext

def validate_consent(form, field):
    consent = True if field.data == 'True' else False
    individual_answers = [getattr(form, f'q{i}').data for i in range(1,12)]
    if consent and not all(individual_answers):
        raise ValidationError(lazy_gettext("Please tick every box above to consent."))

class ConsentForm(FlaskForm):
    q1 = BooleanField(
        label= lazy_gettext("I confirm that I have read and understand the information for the above study "
        "and have had the opportunity to properly consider the information provided."),
        validators=[],
    )
    q2 = BooleanField(
        label=lazy_gettext("I understand that my participation is voluntary and that I am free to withdraw "
        "at any time, without giving any reason and without any adverse consequences."),
        validators=[],
    )
    q3 = BooleanField(
        label=lazy_gettext("I understand the risks associated with participating in this study as explained "
        "in the information sheet."),
        validators=[],
    )
    q4 = BooleanField(
        label=lazy_gettext("I understand that a saliva sample will be taken during the study and that this "
        "sample will be tested for COVID-19. I understand that the sample will be destroyed "
        "after completion of this test or if I withdraw my consent."),
        validators=[],

    )
    q5 = BooleanField(
        label=lazy_gettext("I consider these samples a gift to the University of Oxford and the LANBAMA "
        "laboratory and I understand I will not gain any direct personal benefit from this."),
        validators=[],

    )
    q6 = BooleanField(
        label=lazy_gettext("I understand that research data collected during the study may be looked at "
        "by designated individuals from the University of Oxford and IPICYT where it is "
        "relevant to my taking part in this study. I give permission for these individuals "
        "to access my data. I give permission for anonymised data to be made publicly "
        "available at the end of the research."),
        validators=[],

    )
    q7 = BooleanField(
        label=lazy_gettext("I understand that this project has been reviewed by, and received ethics "
        "clearance through, the Research Ethics Committee at IPICYT and the Central "
        "University Research Ethics Committee at Oxford University"),
        validators=[],

    )
    q8 = BooleanField(
        label=lazy_gettext("I understand who will have access to the personal data provided, how the data "
        "will be stored, and what will happen to the data at the end of the project."),
        validators=[],

    )
    q9 = BooleanField(
        label=lazy_gettext("I understand how this research will be written up and published."),
        validators=[],

    )
    q10 = BooleanField(
        label=lazy_gettext("I understand how to raise a concern or make a complaint."),
        validators=[],

    )
    q11 = BooleanField(
        label=lazy_gettext("I agree to take part in this study."),
        validators=[],
    )
    consent = RadioField(
        label=lazy_gettext("By selecting “Yes, I agree to participate” below you are signifying that you "
        "have read and understood the above information and are agreeing to have the data that "
        "you provide during the course of the study to be processed accordingly."),
        validators=[InputRequired(), validate_consent],
        choices = [
            (True, lazy_gettext("Yes, I agree to participate")),
            (False, lazy_gettext("No, I do not agree to participate"))
        ]
    )
    submit = SubmitField(lazy_gettext('Submit'))

class BaselineSocioDemographicForm(FlaskForm):
    role = RadioField( #Socio-demographic attributes
        label=lazy_gettext("What is your role at the university?"),
        choices = [
            (1, lazy_gettext('Taught student')),
            (2, lazy_gettext('Research student')),
            (3, lazy_gettext('Researcher')),
            (4, lazy_gettext('Staff (Administration, maintenance, other employees of IPICYT)'))
        ],
        validate_choice=False
    )
    affiliation = RadioField( #Socio-demographic attributes
        label=lazy_gettext("Which department are you affiliated with?"),
        choices = [
            (1, lazy_gettext("Molecular Biology Division")),
            (2, lazy_gettext("Environmental Sciences Division")),
            (3, lazy_gettext("Control and Dynamic Systems Divison")),
            (4, lazy_gettext("Applied Geosciences Divison")),
            (5, lazy_gettext("Advanced Materials Divison")),
            (6, lazy_gettext("Computer Science and Engineering Group")),
            (7, lazy_gettext("N/A (Staff)"))
        ],
        validate_choice=False
    )
    gender = RadioField(
        label= lazy_gettext("Which gender do you identify with?"), #Socio-demographic attributes
        choices = [
            (1, lazy_gettext('Female')),
            (2, lazy_gettext('Male')),
            (3, lazy_gettext('Other')),
            (4, lazy_gettext('Prefer not to say'))
        ],
        validate_choice=False
    )
    age = IntegerField(
        label= lazy_gettext("Please indicate your age in two digits"), #Socio-demographic attributes
        validators=[Optional(), NumberRange(min=18, max=99)],
        render_kw={'style': 'width: 5em'}
    )
    ethnicity = RadioField(
        label=lazy_gettext("Which ethnic group do you identify most with?"), #Socio-demographic attributes
        choices=[
            (1, lazy_gettext('White')),
            (2, lazy_gettext('Indigenous')),
            (3, lazy_gettext('Mestizo')),
            (4, lazy_gettext('Afrolatino')),
            (5, lazy_gettext('Other'))
        ],
        validate_choice=False
    )
    next = SubmitField(lazy_gettext('next'))

class BaselineHealthForm(FlaskForm):
    transport = RadioField( #health probabilities
        label=lazy_gettext("What form of transport do you use in your work commute?"),
        choices = [
            (1, lazy_gettext('Private automobile')),
            (2, lazy_gettext('Public transport (bus)')),
            (3, lazy_gettext('Public transport (taxi, uber)'))
        ],
        validate_choice=False
    )
    vaccinestatus = RadioField( #health probabilities
        label=lazy_gettext("Have you been vaccinated against COVID-19?"),
        choices = [
            (1, lazy_gettext("Yes")),
            (2, lazy_gettext("No")),
            (3, lazy_gettext("Prefer not to say"))
        ],
        validate_choice=False
    )
    coviddate = RadioField(
        label=lazy_gettext("When did you last receive a COVID-19 vaccine shot?"), #health probabilities
        choices = [
            (1, lazy_gettext('In the past month')),
            (2, lazy_gettext('In the past three months')),
            (3, lazy_gettext('In the past six months')),
            (4, lazy_gettext('Prefer not to say / Not applicable'))
        ],
        validate_choice=False
    )
    illness = RadioField(
        label=lazy_gettext("Have you recently recovered from COVID-19?"), #health probabilities
        choices=[
            (1, lazy_gettext('Yes')),
            (2,lazy_gettext( 'No')),
            (3, lazy_gettext('Prefer not to say'))
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))

class BaselineSocioEconomicForm(FlaskForm):
    dependants = IntegerField( #socioeconomic score (higher, poorer)
        label=lazy_gettext("How many dependants do you have? This could be children, children and partner, other relatives, etc."), 
        validators=[Optional(), NumberRange(min=0, max=100)],
        render_kw={'style': 'width:5em'}
    )
    household_size = IntegerField( # productivity[need for institutional facilities to be productive] (high numbers, low prod)
        label=lazy_gettext("How many people live in the same household as you? This could be children, children and partner, siblings, other relatives, housemates, etc."),
        validators=[Optional(), NumberRange(min=0, max=100)], 
        render_kw={'style': 'width:5em'}
    )
    socioeconomic_class1 =StringField(
        label=lazy_gettext("Look at the image of the ladder below. Imagine this ladder pictures how Mexican society is set up:"),
    render_kw={'style': 'display: none'}
    )
    socioeconomic_class2 =StringField(
        label=Markup("<div class='my-4'><img src='/static/McArthur_ladder.png' class='mx-auto d-block' style='height: 15em'></img></div>"),
        render_kw={'style': 'display: none'}
    )
    socioeconomic_class3 =StringField(
        label=lazy_gettext("<ul>"
        "<li>At the top of the ladder are the people that are best off - they have the most money, the highest amount of schooling, and the jobs that bring the most respect.</li>"
        "<li>At the bottom are the people who are the worst off - they have the least money, little or no education, no job or jobs that no one wants or respects.</li>"
        "</ul>"),
        render_kw={'style': 'display: none'}
    )
    socioeconomic_class = IntegerField(
        label=(lazy_gettext("<p>Now think of your family. Tell us where you think your family would be on this ladder.</p>")),
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'style': 'width: 5em'}
    )
    perceived_class = RadioField( #socioeconomic score (lower, richer/low utility; prefer not to answer NULL)
        label=lazy_gettext("People sometimes describe themselves as belonging to the working class, the middle class, or the upper or lower class. Would you describe yourself as belonging to the"),
        choices=[
            (1, lazy_gettext('Upper class')),
            (2, lazy_gettext('Upper middle class')),
            (3, lazy_gettext('Lower middle class')),
            (4, lazy_gettext('Working class')),
            (5, lazy_gettext('Lower class')),
            (0, lazy_gettext('Prefer not to answer'))
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))

class BaselineDigitalMediaForm(FlaskForm):
    computer_time = RadioField(
        label=lazy_gettext("How much of your time during a normal work day do you spend working on a computer?"), # productivity[need for institutional facilities to be productive]  
        choices=[
            (5, '0-10%'),
            (4, '11-30%'),
            (3, '31-50%'),
            (2, '51-70%'),
            (1, '71-100%')
        ],
        validate_choice=False
    )
    communication_time = RadioField( # productivity[need for institutional facilities to be productive] 
        label=lazy_gettext("How much of your time during a normal work day do you spend on communication with colleagues?"),  
        choices=[
            (1, '0-10%'),
            (2, '11-30%'),
            (3, '31-50%'),
            (4, '51-70%'),
            (5, '71-100%')
        ],
        validate_choice=False
    )
    teamwork_time = RadioField( # productivity[need for institutional facilities to be productive] (higher percentage/higher utility)
        label=lazy_gettext("How much of your time during a normal work day do you spend working in a team?"),
        choices=[
            (1, '0-10%'),
            (2, '11-30%'),
            (3, '31-50%'),
            (4, '51-70%'),
            (5, '71-100%')
        ],
        validate_choice=False
    )
    work_internet_time = RadioField( # productivity[need for institutional facilities to be productive] (higher percentage / higher utility)
        label=lazy_gettext("How much of your work time do you spend using the internet?"),
        choices=[
            (5, '0-10%'),
            (4, '11-30%'),
            (3, '31-50%'),
            (2, '51-70%'),
            (1, '71-100%')
        ],
        validate_choice=False
    )
    leisure_internet_time = RadioField( # productivity[need for institutional facilities to be productive] 
        label=lazy_gettext("How much of your leisure time do you spend using the internet?"), 
        choices=[
            (5, '0-10%'),
            (4, '11-30%'),
            (3, '31-50%'),
            (2, '51-70%'),
            (1, '71-100%')
        ],
        validate_choice=False
    )
    internet_access = RadioField(
        label=lazy_gettext("How do you usually access the internet from home?"),
        choices=[
            (1, lazy_gettext("Through laptop + wifi")),
            (2, lazy_gettext("Through laptop + mobile connection")),
            (3, lazy_gettext("Through phone + wifi")),
            (4, lazy_gettext("Through phone + mobile connection")),
            (5, lazy_gettext("N/A"))
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))

class BaselinePsychosocialForm(FlaskForm):
    sociability = IntegerField( #psychological score (high percentage, high score)
        label = lazy_gettext("Please write down the percentage of individuals (in your social circle) who would agree with the following statement about yourself: 'I spend a lot of time visiting friends'"),
        validators=[Optional(), NumberRange(min=0, max=100)],
        render_kw={'style': 'width: 5em'}
    )
    fear = RadioField( #psychological score (1 high utility, 5 low utility)
        label=lazy_gettext("Please rate the extent to which you experience the following feelings at this moment: Fear because of the COVID-19 disease/ the SARS COV-2 virus."),
        choices = [
            (1, lazy_gettext("Not at all")),
            (2, lazy_gettext("Not really")),
            (3, lazy_gettext("Neutral")),
            (4, lazy_gettext("Somewhat")),
            (5, lazy_gettext("Very much")),
        ],
        validate_choice=False
    )
    hidden1 = StringField( #psychological score (high stress high utility, low stress low utility)... this is a composite average: 
        label=Markup("<div class='my-2'><img src='/static/scale2.png' class='mx-auto d-block' style='width: 65%'></img></div>"),
        render_kw={'style': 'display: none'}
    )
    hidden2 = StringField( #psychological score (high stress high utility, low stress low utility)... this is a composite average: 
        label=lazy_gettext(
            "Based on the scale above, where 1 indicates never experiencing that situation and 5 indicates experiencing that situation very often, please rate the following statements:"
        ),
        render_kw={'style': 'display: none'}
    )
    stress1 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt that you were unable to control the important things in your life?"),
        validators=[Optional(), NumberRange(min=1, max=5)], #1 low stress 5 high stress
        render_kw={'style': 'width: 5em'}
    )
    stress2 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt confident about your ability to handle your personal problems?"),
        validators=[Optional(), NumberRange(min=1, max=5)], # 1 high stress 5 low stress RECODE
        render_kw={'style': 'width: 5em'}
    )
    stress3 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt that things were going your way?"), # 1 high stress 5 low stress RECODE
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'style': 'width: 5em'}
    )
    stress4 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?"),
        validators=[Optional(), NumberRange(min=1, max=5)], # 1 low stress 5 high stress
        render_kw={'style': 'width: 5em'}
    )
    life_satisfaction = IntegerField( #psychological score (1 high utility 10 low utility) OUTCOME VECTOR
        label=lazy_gettext("All things considered, how satisfied would you say you are with your life these days? Please tell me on a scale of 1 to 10, where 1 means very dissatisfied and 10 means very satisfied:"),
        validators=[Optional(), NumberRange(min=1, max=10)], 
        render_kw={'style': 'width: 5em'}
    )
    institute_satisfaction = IntegerField( # psychology OUTCOME VECTOR
        label=lazy_gettext("Taking all things together on a scale of 1 to 10, how satisfied are you about IPICYT's efforts to keep you safe in the institute throughout the pandemic?"),
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'style': 'width: 5em'}
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))

class BaselinePerformanceForm(FlaskForm):
    overall = RadioField( # Self-assessment of performance OUTCOME
        label=lazy_gettext("How would you rate your overall performance for your job or degree in the past 4 weeks?"),
        choices=[
            (5, lazy_gettext('Poor')),
            (4, lazy_gettext('Below average')),
            (3, lazy_gettext('Average')),
            (2, lazy_gettext('Above average')),
            (1, lazy_gettext('High'))
        ],
        validate_choice=False
    )
    learning = IntegerField( # Self-assessment of learning OUTCOME
        label=lazy_gettext("After the COVID-19 pandemic began, the way we learn and interact with our peers drastically changed. How would you say your learning experience has been in the past 4 weeks? "
        "Please rate your learning process and experience between 1 and 10, where 1 is poor and 10 is excellent:"),
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'style': 'width: 5em'}
    )
    productivity = RadioField( # Self-assessment of productivity
        label=lazy_gettext("How would you rate your day-to-day productivity in your work in the past 4 weeks?"),
        choices=[
            (5, lazy_gettext('Poor')),
            (4, lazy_gettext('Below average')),
            (3, lazy_gettext('Average')),
            (2, lazy_gettext('Above average')),
            (1, lazy_gettext('High'))
        ],
        validate_choice=False
    )
    supervisor_goals = RadioField( # Self-assessment of performance (supervisory goals)
        label=lazy_gettext("Considering again the work for your job or degree during the past 4 weeks, please select the statement that fits your situation best."),
        choices=[
            (5, lazy_gettext('I have struggled to achieve the goals set by my supervisor/employer/course teachers')),
            (4, lazy_gettext('I have managed to achieve some of the goals set by my supervisor/employer/course teachers')),
            (3, lazy_gettext('I have achieved many of the goals set by my supervisor/employer/course teachers')),
            (2, lazy_gettext('I have achieved most of the goals set by my supervisor/employer/course teachers')),
            (1, lazy_gettext('I have achieved all or exceeded the goals set by my supervisor/employer/course teachers')),
        ],
        validate_choice=False
    )
    own_goals = RadioField( #Self-assessment of performance (own)
        label=lazy_gettext("Considering again the work for your job or degree during the past 4 weeks, please select the statement that fits your situation best."),
        choices=[
            (5, lazy_gettext('I have struggled to achieve the goals I set for myself')),
            (4, lazy_gettext('I have managed to achieve some of the goals I set for myself')),
            (3, lazy_gettext('I have achieved many of the goals I set for myself')),
            (2, lazy_gettext('I have achieved most of the goals I set for myself')),
            (1, lazy_gettext('I have achieved all or exceeded the goals I set for myself')),
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('finish'))


class EndlineSocioEconomicForm(FlaskForm):
    communication_time = RadioField(
        label=lazy_gettext("How much of your time during a normal work day do you spend on communication with colleagues?"),
        choices=[
            (1, '0-10%'),
            (2, '11-30%'),
            (3, '31-50%'),
            (4, '51-70%'),
            (5, '71-100%')
        ],
        validate_choice=False
    )
    teamwork_time = RadioField(
        label=lazy_gettext("How much of your time during a normal work day do you spend working in a team?"),
        choices=[
            (1, '0-10%'),
            (2, '11-30%'),
            (3, '31-50%'),
            (4, '51-70%'),
            (5, '71-100%')
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))
    
class EndlineHealthForm(FlaskForm):
    covid_diagnose = RadioField(
        label=lazy_gettext("Were you diagnosed with COVID-19 in the past month?"),
        choices=[
            (1, lazy_gettext('Yes')),
            (2, lazy_gettext('No')),
            (3, lazy_gettext('Prefer not to say'))
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))

class EndlinePsychosocialForm(FlaskForm):
    sociability = IntegerField(
        label = lazy_gettext("Please write down the percentage of individuals (in your social circle) who would agree with the following statement about yourself: 'I spend a lot of time visiting friends'"),
        validators=[Optional(), NumberRange(min=0, max=100)],
        render_kw={'style': 'width: 5em'}
    )
    fear = RadioField(
        label=lazy_gettext("Please rate the extent to which you experience the following feelings at this moment: Fear because of the COVID-19 disease/ the SARS COV-2 virus."),
        choices = [
            (1, lazy_gettext("Not at all")),
            (2, lazy_gettext("Not really")),
            (3, lazy_gettext("Neutral")),
            (4, lazy_gettext("Somewhat")),
            (5, lazy_gettext("Very much")),
        ],
        validate_choice=False
    )
    hidden = StringField(
        label=Markup(lazy_gettext(
            "<div class='my-2'><img src='/static/scale.png' class='mx-auto d-block' style='width: 65%'></img></div>"
            "Based on the scale above, where 1 indicates never experiencing that situation and 5 indicates experiencing that situation very often, please rate the following statements:"
        )),
        render_kw={'style': 'display: none'}
    )
    stress1 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt that you were unable to control the important things in your life?"),
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'style': 'width: 5em'}
    )
    stress2 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt confident about your ability to handle your personal problems?"),
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'style': 'width: 5em'}
    )
    stress3 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt that things were going your way?"),
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'style': 'width: 5em'}
    )
    stress4 = IntegerField(
        label=lazy_gettext("In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?"),
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'style': 'width: 5em'}
    )
    life_satisfaction = IntegerField(
        label=lazy_gettext("All things considered, how satisfied would you say you are with your life these days? Please tell me on a scale of 1 to 10, where 1 means very dissatisfied and 10 means very satisfied:"),
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'style': 'width: 5em'}
    )
    institute_satisfaction = IntegerField(
        label=lazy_gettext("Taking all things together on a scale of 1 to 10, how satisfied are you about IPICYT's efforts to keep you safe in the institute throughout the pandemic?"),
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'style': 'width: 5em'}
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('next'))

class EndlinePerformanceForm(FlaskForm):
    overall = RadioField(
        label=lazy_gettext("How would you rate your overall performance for your job or degree in the past 4 weeks?"),
        choices=[
            (5, lazy_gettext('Poor')),
            (4, lazy_gettext('Below average')),
            (3, lazy_gettext('Average')),
            (2, lazy_gettext('Above average')),
            (1, lazy_gettext('High')),
        ],
        validate_choice=False
    )
    learning = IntegerField(
        label=lazy_gettext("After the COVID-19 pandemic began, the way we learn and interact with our peers drastically changed. How would you say your learning experience has been in the past 4 weeks? "
        "Please rate your learning process and experience between 1 and 10, where 1 is poor and 10 is excellent:"),
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'style': 'width: 5em'}
    )
    productivity = RadioField(
        label=lazy_gettext("How would you rate your day-to-day productivity in your work in the past 4 weeks?"),
        choices=[
            (5, lazy_gettext('Poor')),
            (4, lazy_gettext('Below average')),
            (3, lazy_gettext('Average')),
            (2, lazy_gettext('Above average')),
            (1, lazy_gettext('High')),
        ],
        validate_choice=False
    )
    supervisor_goals = RadioField(
        label=lazy_gettext("Considering again the work for your job or degree during the past 4 weeks, please select the statement that fits your situation best."),
        choices=[
            (5, lazy_gettext('I have struggled to achieve the goals set by my supervisor/employer/course teachers')),
            (4, lazy_gettext('I have managed to achieve some of the goals set by my supervisor/employer/course teachers')),
            (3, lazy_gettext('I have achieved many of the goals set by my supervisor/employer/course teachers')),
            (2, lazy_gettext('I have achieved most of the goals set by my supervisor/employer/course teachers')),
            (1, lazy_gettext('I have achieved all or exceeded the goals set by my supervisor/employer/course teachers')),
        ],
        validate_choice=False
    )
    own_goals = RadioField(
        label=lazy_gettext("Considering again the work for your job or degree during the past 4 weeks, please select the statement that fits your situation best."),
        choices=[
            (5, lazy_gettext('I have struggled to achieve the goals I set for myself')),
            (4, lazy_gettext('I have managed to achieve some of the goals I set for myself')),
            (3, lazy_gettext('I have achieved many of the goals I set for myself')),
            (2, lazy_gettext('I have achieved most of the goals I set for myself')),
            (1, lazy_gettext('I have achieved all or exceeded the goals I set for myself')),
        ],
        validate_choice=False
    )
    prev = SubmitField(lazy_gettext('prev'), render_kw = {'class': 'btn-secondary'})
    next = SubmitField(lazy_gettext('finish'))