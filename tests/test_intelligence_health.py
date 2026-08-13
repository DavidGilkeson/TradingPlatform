from paper_trading.intelligence_health import _grade, _status

def test_health_grades():
    assert _grade(90)=="A"
    assert _grade(75)=="B"
    assert _grade(60)=="C"
    assert _grade(45)=="D"
    assert _grade(20)=="Early"

def test_health_statuses():
    assert _status(90)=="Strong evidence base"
    assert _status(75)=="Healthy and developing"
    assert _status(60)=="Developing evidence"
    assert _status(45)=="Limited evidence"
    assert _status(20)=="Too early to rely on heavily"
