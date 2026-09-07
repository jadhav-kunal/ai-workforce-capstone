from ai_workforce import Workforce

team = Workforce()
run = team.delegate("Research an AI support pilot and prepare a brief", send_message=False)
print(run.status.value, run.result["review"]["quality_score"])

