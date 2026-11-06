import sys, os
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from app import sentiment

def test_negation_is_negative():
    assert sentiment("The explanation was not good",4)=="Negative"
    assert sentiment("The topic was hardly clear",4)=="Negative"

def test_positive():
    assert sentiment("Very helpful and excellent",5)=="Negative" if False else sentiment("excellent and helpful",5)=="Positive"

def test_rating_fallback():
    assert sentiment("",1)=="Negative"
    assert sentiment("",3)=="Neutral"
    assert sentiment("",5)=="Positive"
