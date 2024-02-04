#
# A utility class to work with tensorboards
#
import google.cloud.aiplatform as aip 
from google.api_core import exceptions

class TensorBoardExperimentRun:

    def __init__(self, experiment_name, experiment_run_name, google_project_id, google_region):
        """
        Initialize a tensor board experiment run. This assumes that the experiment exists
        and has a backing tensorboard. During initialization, we create a tensorboard experiment
        if it does not exist yet and a tensorboard run if it does not exist. 

        Args:
            experiment_name (str):
                Required. The name of the experiment (must exist)
            experiment_run_name (str):
                Required. The name of the experiment run
            google_project_id (str):
                Required. Project to retrieve tensorboard from 
            google_region (str):
                Required. Location to retrieve tensorboard from

        """
        self._labels = set()
        self._google_project_id = google_project_id
        self._google_region = google_region
        #
        # Get our experiment
        #
        self._experiment_name = experiment_name
        self._experiment_run_name = experiment_run_name
        aip.init(
            project = google_project_id,
            location = google_region,
            experiment = experiment_name
        )
        self._experiment = aip.Experiment.get(experiment_name)
        assert self._experiment is not None, f"Could not find experiment {experiment_name}"
        #
        # Get resource name of backing tensorboard 
        #
        backing_tensorboard_resource_name = self._experiment.backing_tensorboard_resource_name
        assert backing_tensorboard_resource_name is not None, "Could not find backing tensorboard for this experiment, did you use init?"
        self._backing_tensorboard = aip.Tensorboard(backing_tensorboard_resource_name)
        #
        # Create a tensorboard experiment if it does not yet exist. Note that we need to use the same name
        # as the underlying Vertex AI experiment so that the console can associate these two items and display
        # the correct link
        #
        try:
            tb_experiment = aip.TensorboardExperiment(
            tensorboard_experiment_name = f"{backing_tensorboard_resource_name}/experiments/{self._experiment_name}"
            )
        except exceptions.NotFound:
            tb_experiment = aip.TensorboardExperiment.create(
                tensorboard_experiment_id = self._experiment_name,
                tensorboard_name = backing_tensorboard_resource_name,
                #
                # Adding this label avoids that the experiment is displayed on the console
                # separately from our actual experiment
                #
                labels = { "vertex_tensorboard_experiment_source": "vertex_experiment" }
            )
        self._tb_experiment = tb_experiment
        #
        # Create a tensorboard experiment run
        # 
        try:
            tb_run = aip.TensorboardRun(
                tensorboard_run_name = self._experiment_run_name,
                tensorboard_id = self._backing_tensorboard.resource_name.split("/")[-1],
                tensorboard_experiment_id = tb_experiment.resource_name.split("/")[-1],
                project = google_project_id,
                location = google_region
            )
        except exceptions.NotFound:
            tb_run = aip.TensorboardRun.create(
                tensorboard_run_id = self._experiment_run_name,
                tensorboard_experiment_name = self._experiment_name,
                tensorboard_id = self._backing_tensorboard.resource_name.split("/")[-1],
            )
        self._tb_run = tb_run
        #
        # Get all time series and see which display names we already have
        #
        tb_keys = [ts.display_name for ts in  aip.TensorboardTimeSeries.list(
            tensorboard_run_name = tb_run.resource_name
        )]
        self._labels = set(tb_keys)

    def log_time_series_metrics(self, metrics, step):
        """
        Log a time series metric. 

        Args:
            metrics (dict):
                Required. The metrics to be logged, a dictionary of labels and scalar values
            step (int):
                Required. The step 

        """
        for label in metrics.keys():
            if label not in self._labels:
                self._tb_run.create_tensorboard_time_series(
                    display_name = label
                )
                self._labels.add(label)
            #
            # log data
            #
            self._tb_run.write_tensorboard_scalar_data({
                            label : metrics[label]
                        }, step = step)
    

    

