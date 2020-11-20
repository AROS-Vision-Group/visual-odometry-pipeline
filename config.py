from sys import argv
import detector
import cv2


class DefaultConfig:
    def __init__(self, configuration):
        defaults = configuration["DEFAULTS"]
        self.W = defaults["W"]
        self.H = defaults["H"]
        self.pin_hole_params = defaults["PIN_HOLE_PARAMS"]
        self.images = defaults["IMAGES"]
        self.annotations = defaults["ANNOTATIONS"]


class Config(DefaultConfig):
    def __init__(self, configuration):
        super().__init__(configuration)
        self.defaults = configuration["DEFAULTS"]

        try:
            self.experiment_info = str(argv[1]).upper()
            self.experiment = configuration[self.experiment_info]
            self.name = self.experiment_info
            self.toggle_morphology = self.experiment["toggle_morphology"]
            self.detector_params = self.experiment["detector_params"]
            self.extractor_params = self.experiment["extractor_params"]
            self.k_min_features = self.experiment["k_min_features"]
            self.flann_params = self.experiment["flann_params"]
            self.k_min_features = self.experiment["k_min_features"]
            self.parse_lk_params(self.experiment["lk_params"])
            self.parse_experiment_args()
            self.parse_detector(self.detector)
            self.parse_extractor(self.extractor)
        except Exception as ex:
            pass

    def parse_lk_params(self, lk_parmas_dict):
        params = {} if lk_parmas_dict is None else lk_parmas_dict
        try:
            for key, values in params.items():
                if key.upper() == "CRITERIA":
                    criteria_one = values[0]
                    criteria_two = values[1]
                    max_iterations = values[2]
                    epsilon = values[3]
                    params["criteria"] = (criteria_one | criteria_two, max_iterations, epsilon)
            self.lk_params = params
        except Exception as ex:
            pass

    def parse_detector(self, detector_string):
        params = {} if self.detector_params is None else self.detector_params

        if detector_string.upper() == "FAST":
            self.detector = detector.FAST_Detector(**params)
        elif detector_string.upper() == "CENSURE":
            self.detector = detector.CenSurE_Detector(**params)
        elif detector_string.upper() == "SIFT":
            self.detector = detector.SIFT(**params)
        elif detector_string.upper() == "SURF":
            self.detector = detector.SURF(**params)
        elif detector_string.upper() == "ORB":
            self.detector = detector.ORB(**params)
        elif detector_string.upper() == "AKAZE":
            self.detector = detector.AKAZE(**params)
        elif detector_string.upper() == "SHI":
            self.detector = detector.ShiTomasiDetector(**params)
        else:
            raise ModuleNotFoundError(f"No detector <{detector_string}> found.")

    def parse_extractor(self, extractor_string):
        as_extractor = False
        if self.experiment["detector"] != extractor_string:
            as_extractor = True

        params = {} if self.extractor_params is None else self.extractor_params

        if extractor_string.upper() == "SIFT":
            self.extractor = detector.SIFT(as_extractor=as_extractor, **params)
        elif extractor_string.upper() == "SURF":
            self.extractor = detector.SURF(as_extractor=as_extractor, **params)
        elif extractor_string.upper() == "ORB":
            self.extractor = detector.ORB(as_extractor=as_extractor, **params)
        elif extractor_string.upper() == "AKAZE":
            self.extractor = detector.AKAZE(as_extractor=as_extractor, **params)
        elif extractor_string.upper() == "BRIEF":
            self.extractor = detector.BRIEF_Extractor(**params)
        else:
            raise ModuleNotFoundError(f"No descriptor extractor <{extractor_string}> found.")

    def parse_experiment_args(self):
        INFO = self.experiment_info.split("_")
        self.correspondence_method = 'tracking' if INFO[0].upper() == 'AB' else 'matching'
        if len(INFO) == 2:
            self.detector = INFO[1]
            self.extractor = None
        elif len(INFO) == 3:
            self.detector = INFO[1]
            self.extractor = INFO[2]