#
# Play around with tensorboards
#
import google.cloud.aiplatform as aip 
import os 
import tb_utils

    

google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")

EXPERIMENT_NAME = "tbtest-experiment"
#
# Make sure that there is an experiment
#
aip.init(project = google_project_id,
         location = google_region,
         experiment = EXPERIMENT_NAME)


#
# Create run
#
tb_run = tb_utils.TensorBoardExperimentRun(
    google_project_id = google_project_id,
    google_region = google_region,
    experiment_name = EXPERIMENT_NAME,
    experiment_run_name = "my-run"
)

#
# Log something
#
for step in range(20):
    tb_run.log_time_series_metrics({
        "loss" : 1.0 - 0.001*step,
    }, step = step)

