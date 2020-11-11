import numpy as np
import cv2

STAGE_FIRST_FRAME = 0
STAGE_SECOND_FRAME = 1
STAGE_DEFAULT_FRAME = 2
kMinNumFeature = 450

lk_params = dict(winSize=(21, 21),
                maxLevel = 5,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))

# Params for ShiTomasi corner detection
# feature_params = dict(maxCorners=300,
#                      qualityLevel=0.03,
#                      minDistance=50,
#                      blockSize=10)


def featureTracking(image_ref, image_cur, px_ref):
    kp2, st, err = cv2.calcOpticalFlowPyrLK(image_ref, image_cur, px_ref, None, **lk_params)  # shape: [k,2] [k,1] [k,1]
    st = st.reshape(st.shape[0])
    kp1 = px_ref[st == 1]
    kp2 = kp2[st == 1]
    return kp1, kp2



class VisualOdometry:
    def __init__(self, cam, annotations):
        self.frame_stage = 0
        self.cam = cam
        self.new_frame = None
        self.last_frame = None
        self.cur_R = None
        self.prev_t = None
        self.cur_t = None
        self.px_ref = None
        self.px_cur = None
        self.focal = cam.fx
        self.pp = (cam.cx, cam.cy)
        self.trueX, self.trueY, self.trueZ = 0, 0, 0
        self.detector = cv2.FastFeatureDetector_create(threshold=10, nonmaxSuppression=True)
        with open(annotations) as f:
            self.annotations = f.readlines()

    def get_absolute_scale(self, frame_id):
        xi, yi, zi = 3, 7, 11
        ss = self.annotations[frame_id - 1].strip().split()
        x_prev = float(ss[xi])
        y_prev = float(ss[yi])
        z_prev = float(ss[zi])
        ss = self.annotations[frame_id].strip().split()
        x = float(ss[xi])
        y = float(ss[yi])
        z = float(ss[zi])
        self.trueX, self.trueY, self.trueZ = x, y, z
        return np.sqrt((x - x_prev) * (x - x_prev) + (y - y_prev) * (y - y_prev) + (z - z_prev) * (z - z_prev))

    def get_relative_scale(self):
        """
        Triangulate 3-D points X_(k-1) and X_k from current and previous frame to get relative scale
        :return: relative scale of translation between previous and current frame
        """
        point_distances_prev = np.array([np.sqrt((self.px_ref[i + 1][0] - self.px_ref[i][0])**2) for i in range(len(self.px_ref) - 1)])
        point_distances_cur = np.array([np.sqrt((self.px_cur[i + 1][0] - self.px_cur[i][0])**2) for i in range(len(self.px_cur) - 1)])
        # z_change = np.linalg.norm(feature_distances_new, feature_distances_old)
        rel_scale = np.median(point_distances_prev / point_distances_cur)
        return rel_scale

    def process_initial_frame(self):
        self.px_ref = self.detector.detect(self.new_frame)
        self.px_ref = np.array([x.pt for x in self.px_ref], dtype=np.float32)
        self.frame_stage = STAGE_SECOND_FRAME

    def process_second_frame(self):
        self.px_ref, self.px_cur = featureTracking(self.last_frame, self.new_frame, self.px_ref)
        E, mask = cv2.findEssentialMat(self.px_cur, self.px_ref, focal=self.focal, pp=self.pp, method=cv2.RANSAC,
                                       prob=0.999, threshold=1.0)
        _, self.cur_R, self.cur_t, mask = cv2.recoverPose(E, self.px_cur, self.px_ref, focal=self.focal, pp=self.pp)
        self.frame_stage = STAGE_DEFAULT_FRAME
        self.px_ref = self.px_cur

    def process_frame(self, frame_id):
        self.px_ref, self.px_cur = featureTracking(self.last_frame, self.new_frame, self.px_ref)
        E, mask = cv2.findEssentialMat(self.px_cur, self.px_ref, focal=self.focal, pp=self.pp, method=cv2.RANSAC,
                                       prob=0.999, threshold=1.0)
        _, R, t, mask = cv2.recoverPose(E, self.px_cur, self.px_ref, focal=self.focal, pp=self.pp)

        self.prev_t = self.cur_t
        relative_scale = self.get_relative_scale()
        absolute_scale = self.get_absolute_scale(frame_id)

        if (absolute_scale > 0.01):
            self.cur_t = self.cur_t + absolute_scale * self.cur_R.dot(t)
            self.cur_R = R.dot(self.cur_R)
        if (self.px_ref.shape[0] < kMinNumFeature):
            self.px_cur = self.detector.detect(self.new_frame)
            self.px_cur = np.array([x.pt for x in self.px_cur], dtype=np.float32)
        self.px_ref = self.px_cur

    def update(self, img, frame_id):
        assert (img.ndim == 2 and img.shape[0] == self.cam.height and img.shape[1] == self.cam.width), \
            "Frame: provided image has not the same size as the camera model or image is not grayscale"

        self.new_frame = img
        if (self.frame_stage == STAGE_DEFAULT_FRAME):
            self.process_frame(frame_id)
        elif (self.frame_stage == STAGE_SECOND_FRAME):
            self.process_second_frame()
        elif (self.frame_stage == STAGE_FIRST_FRAME):
            self.process_initial_frame()
        self.last_frame = self.new_frame
