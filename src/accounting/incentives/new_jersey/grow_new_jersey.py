from accounting.incentives import *


class IncentiveProgram(IncentiveProgramBase):
    def __init__(self, **kwargs):
        self.project_level_inputs = kwargs['project_level_inputs']
        self.median_salary = kwargs['state_to_prevailing_wages']['New Jersey']
        self.promised_jobs = kwargs['project_level_inputs']['Promised jobs']

    def estimated_eligibility(self) -> bool:
        if self.promised_jobs >= 10:
            return True
        return False

    def estimated_incentives(self) -> List[float]:
        incentives = [0.0]
        maximum_annual_cap = 10_000_000.0

        bonus = 0.0
        base = 5000.0

        if self.project_level_inputs['Promised wages'] >= self.median_salary:
            bonus += 1500

        if self.promised_jobs > 1000:
            bonus += 1500
        elif self.promised_jobs > 800:
            bonus += 1250
        elif self.promised_jobs > 600:
            bonus += 1000
        elif self.promised_jobs > 400:
            bonus += 750
        elif self.promised_jobs > 250:
            bonus += 500

        if self.project_level_inputs['High-level category'] in [
            'Manufacturing',
            'Information',
            'Finance and insurance',
            'Health care and social assistance',
            'Distribution center'
        ]:
            bonus += 500

        per_job_total = base + bonus
        maximum_per_job = 15_000.0

        for i in range(10):
            incentive = min([per_job_total, maximum_per_job]) * self.promised_jobs
            incentives.append(
                min([maximum_annual_cap, incentive])
            )
        return incentives
