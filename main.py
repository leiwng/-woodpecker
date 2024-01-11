"""
Module for getting chromosome image, mask and contour with chromosome id from karyotype image.

Usage:
    - Import this module using `import mymodule`.
    - Use the functions provided by this module as needed.

Author: Lei Wang
Date: Dec 14, 2023
"""

__author__ = "王磊"
__copyright__ = "Copyright 2023 四川科莫生医疗科技有限公司"
__credits__ = ["王磊"]
__maintainer__ = "王磊"
__email__ = "lei.wang@kemoshen.com"
__version__ = "0.0.1"
__status__ = "Development"

import os
import cv2

from karyotype import Karyotype


KYT_IMG_FP = "D:\\Prj\\github\\woodpecker\\test\\test_img\\L2311245727.001.K.TIF"
karyotype_chart = Karyotype(KYT_IMG_FP)
karyotype_chart.read_karyotype()

canvas = cv2.imread(KYT_IMG_FP)

for cntrs in karyotype_chart.id_cntr_dicts_orgby_cy.values():
    for cntr in cntrs:
        cv2.drawContours(canvas, [cntr["cntr"]], -1, (0, 255, 0), 1)

for cntrs in karyotype_chart.chromo_cntr_dicts_orgby_cy.values():
    for idx, cntr in enumerate(cntrs):
        cv2.drawContours(canvas, [cntr["cntr"]], -1, (0, 0, 255), 1)
        x = cntr["cx"]
        y = cntr["cy"]
        if idx % 2 == 0:
            cv2.putText(
                canvas,
                cntr["chromo_id"],
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 0, 0),
                1,
            )
        else:
            cv2.putText(
                canvas,
                cntr["chromo_id"],
                (x - 8, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 0, 0),
                1,
            )

kyt_img_dir, kyt_img_fn = os.path.split(KYT_IMG_FP)
kyt_img_fbasename = os.path.splitext(kyt_img_fn)[0]
net_img_fp = f"{os.path.join(kyt_img_dir, kyt_img_fbasename)}_id-on-cntr.png"
cv2.imwrite(net_img_fp, canvas)
