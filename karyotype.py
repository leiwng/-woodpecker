'''
Module for Chromosome Karyotype Chart.
1. Get chromosome contour information with chromosome id;
2. Chromosome contour information including:
 1) chromosome id, from 1 to 22, X, Y; ['chromo_id']
 2) chromosome index, from 0 to 23; X is 22, Y is 23; ['chromo_idx']
 3) chromosome contour; ['cntr']
 4) chromosome contour area; ['area']
 5) chromosome contour bounding rectangle; ['rect']
 6) chromosome contour center point; ['cx'],['cy']
 7) chromosome contour index(核型图所有轮廓的index); ['cntr_idx']
 8) chromosome min area rectangle; ['min_area_rect']

Usage:
    - Import this module using `import mymodule`.
    - Use the functions provided by this module as needed.

Author: Lei Wang
Date: Dec 14, 2023
'''
__author__ = "王磊"
__copyright__ = "Copyright 2023 四川科莫生医疗科技有限公司"
__credits__ = ["王磊"]
__maintainer__ = "王磊"
__email__ = "lei.wang@kemoshen.com"
__version__ = "0.0.1"
__status__ = "Development"


import os
import configparser


import cv2
import numpy as np
from utils.chromo_cv_utils import find_external_contours
from utils.utils import get_distance_between_two_contours, merge_two_contours_by_npi


# 创建配置对象并读取配置文件
cfg = configparser.ConfigParser()
cfg.read('./config/karyotype.ini', encoding='utf-8')

# BinThreshold = 253 ;求轮廓时图像二值化使用的阈值
BIN_THRESH = cfg.getint('General', 'BinThreshold')
# IdCharYTolerance = 4;同排染色体编号高度容差,单位像素
ID_CHAR_Y_TOLERANCE = cfg.getint('General', 'IdCharYTolerance')
# MaxIdCharArea = 80 ;染色体编号字符轮廓最大面积，实际测量为76，为了容差，设置为80
MAX_ID_CHAR_AREA = cfg.getint('General', 'MaxIdCharArea')
#染色体编号字符轮廓最小面积，实际测量为17，为了容差，设置为15
MIN_ID_CHAR_AREA = cfg.getint('General', 'MinIdCharArea')
# 每排染色体编号最少字符数, 实际就是第1排染色体编号字符数, Row1IdCharNum = 5 ;第1排染色体编号字符数
ROW_ID_CHAR_MIN_NUM = cfg.getint('General', 'Row1IdCharNum')
# 每排染色体编号最多字符数, 实际就是第3排染色体编号字符数, Row3IdCharNum = 12 ;第1排染色体编号字符数
ROW_ID_CHAR_MAX_NUM = cfg.getint('General', 'Row3IdCharNum')
# IdCharXTolerance = 40;染色体编号字符x坐标容差,单位像素,实测值为11,但同排不同染色体编号离得非常开,为了容差，设置为40
ID_CHAR_X_TOLERANCE = cfg.getint('General', 'IdCharXTolerance')
# TotalIdNum = 24 ;总染色体编号数
TOTAL_ID_NUM = cfg.getint('General', 'TotalIdNum')
# Row1IdNum = 5 ;第1排染色体编号数 1,2,3,4,5
ROW_1_ID_NUM = cfg.getint('General', 'Row1IdNum')
# Row2IdNum = 7 ;第2排染色体编号数 6,7,8,9,10,11,12
ROW_2_ID_NUM = cfg.getint('General', 'Row2IdNum')
# Row3IdNum = 6 ;第3排染色体编号数 13,14,15,16,17,18
ROW_3_ID_NUM = cfg.getint('General', 'Row3IdNum')
# Row4IdNum = 6 ;第4排染色体编号数 19,20,21,22,X,Y
ROW_4_ID_NUM = cfg.getint('General', 'Row4IdNum')
# SmallPieceAreaRatio = 0.4 ;染色体碎片面积同染色体面积的最大比率
SMALL_PIECE_AREA_RATIO = cfg.getfloat('General', 'SmallPieceAreaRatio')


class Karyotype:
    '''
    Chromosome Karyotype Chart Class

    Attributes:
        attribute1 (int): An integer attribute.
        attribute2 (str): A string attribute.

    Methods:
        method1(): This method does something.
        method2(): This method does something else.

    Usage:
        - Create an instance of MyClass using `obj = MyClass()`.
        - Access attributes and call methods using `obj.attribute1`, `obj.method1()`, etc.
    '''

    def __init__(self, karyotype_img_fp):
        """_summary_

        Args:
            karyotype_img_fp (string): Full path of karyotype image file.

        Raises:
            ValueError: _description_
            FileNotFoundError: _description_
            ValueError: _description_
        """
        if karyotype_img_fp is None:
            raise ValueError('karyotype_img_fp is None')

        if not os.path.exists(karyotype_img_fp):
            raise FileNotFoundError(f'{karyotype_img_fp} is not exists')

        self.img = {'fp': karyotype_img_fp}

        (self.img['fpath'], self.img['fname']) = os.path.split(self.img['fp'])
        (self.case_id, self.pic_id,
            self.img['type'], self.img['fext']) = self.img['fname'].split('.')

        self.img['img'] = cv2.imread(self.img['fp'])
        if self.img['img'] is None:
            raise ValueError(f'{karyotype_img_fp} is not a valid image')

        self.img['height'], self.img['width'], self.img['channels'] = self.img['img'].shape

        # member properties init
        self.cntr_dicts = []  # 核型图中所有轮廓信息

        self.id_cntr_dicts_orgby_cy = {}  # 核型图中染色体编号轮廓信息，按照cy为key进行组织
        self.id_cntr_dicts = []  # 核型图中染色体编号轮廓信息

        self.id_char_cntr_dicts_orgby_cy = {}  # 核型图中染色体字符编号轮廓信息，按照cy为key进行组织
        self.id_char_cntr_dicts = []  # 核型图中染色体编号字符轮廓信息

        self.chromo_cntr_dicts_orgby_cy = {}  # 核型图中染色体轮廓信息，按照cy为key进行组织
        self.chromo_cntr_dicts = []  # 核型图中染色体轮廓信息


    def _id_info(self):
        """ Summary:
                获取核型图上染色体编号信息，该信息用于后续确定染色体编号;
                位于染色体下方，与染色体距离最近的编号，就是该染色体的编号。
            Member Properties Dependence:
                self.cntr_dicts, # 核型图中所有轮廓信息
            Results:
                self.id_char_cntrs_info, # id_char_info (list of list of dict): [
                    [{'cntr_idx':89,'cntr]]],...}, ...], # 第一排染色体编号字符轮廓信息
                    [{'cntr_idx':73,'cntr':[[[x,y]]],...}, ...], # 第二排染色体编号字符轮廓信息
                    [{'cntr_idx':55,'cntr':[[[x,y]]],...}, ...], # 第三排染色体编号字符轮廓信息
                    [{'cntr_idx':41,'cntr':[[[x,y]]],...}, ...], # 第四排染色体编号字符轮廓信息
                ]
                self.id_cntrs_info, # id_info (list of list of dict): [
                    [{'chromo_id':'1','chromo_idx':0,'cp':[x,y]}, ...], # 第一排染色体编号信息, cp为编号中心点坐标
                    [{'chromo_id':'6','chromo_idx':5,'cp':[x,y]}, ...], # 第二排染色体编号信息
                    [{'chromo_id':'13','chromo_idx':12,'cp':[x,y]}, ...], # 第三排染色体编号信息
                    [{'chromo_id':'19','chromo_idx':18,'cp':[x,y]}, ...], # 第四排染色体编号信息
                ]
        """
        # 先根据染色体编号字符的面积大小，过滤掉染色体轮廓
        id_cntr_dicts = [
            cntr_dict for cntr_dict in self.cntr_dicts if cntr_dict['area'] < MAX_ID_CHAR_AREA and cntr_dict['area'] > MIN_ID_CHAR_AREA
        ]

        # 找到同排的染色体编号字符
        # 按照轮廓中心点cy坐标重新组织轮廓信息 orgby: organized by
        id_cntr_dicts_orgby_cy = {}
        for cntr_dict in id_cntr_dicts:
            key = cntr_dict['cy']
            if key not in id_cntr_dicts_orgby_cy:
                id_cntr_dicts_orgby_cy[key] = []
            id_cntr_dicts_orgby_cy[key].append(cntr_dict)

        # 将cy差距小于等于同排染色体编号高度容差的轮廓合并为一组
        merged_id_cntr_dicts_orgby_cy = {}
        merged_keys = []
        for given_key, given_cntr_dicts in id_cntr_dicts_orgby_cy.items():
            if given_key in merged_keys:
                continue
            merged_id_cntr_dicts_orgby_cy[given_key] = given_cntr_dicts
            for chk_key, chk_cntr_dicts in id_cntr_dicts_orgby_cy.items():
                # 下面考虑key2是否需要合并
                if given_key != chk_key and abs(given_key - chk_key) <= ID_CHAR_Y_TOLERANCE and chk_key not in merged_keys:
                    merged_id_cntr_dicts_orgby_cy[given_key] = merged_id_cntr_dicts_orgby_cy[given_key] + chk_cntr_dicts
                    merged_keys.append(chk_key)

        # 去掉轮廓数小于最小每排染色体编号字符数:ROW_ID_CHAR_MIN_NUM
        merged_id_cntr_dicts_orgby_cy = {
            key: merged_id_cntr_dicts_orgby_cy[key] for key in merged_id_cntr_dicts_orgby_cy
                if len(merged_id_cntr_dicts_orgby_cy[key]) >= ROW_ID_CHAR_MIN_NUM and len(merged_id_cntr_dicts_orgby_cy[key]) <= ROW_ID_CHAR_MAX_NUM
        }

        # 判断key个数是否为4，不为4则报错
        if len(merged_id_cntr_dicts_orgby_cy) != 4:
            raise ValueError(f'{self.img["fp"]}染色体编号排的数量为{
                             len(merged_id_cntr_dicts_orgby_cy)},应该为4')

        # 按照cy坐标从小到大排序
        merged_id_cntr_dicts_orgby_cy = dict(
            sorted(merged_id_cntr_dicts_orgby_cy.items(), key=lambda item: item[0]))

        # SAVE RESULT to CLASS INSTANCE MEMBER PROPERTY
        self.id_char_cntr_dicts_orgby_cy = merged_id_cntr_dicts_orgby_cy
        self.id_char_cntr_dicts = [
            merged_id_cntr_dicts_orgby_cy[key] for key in merged_id_cntr_dicts_orgby_cy]

        # 每列的轮廓按x坐标从小到大排序
        for key in merged_id_cntr_dicts_orgby_cy:
            merged_id_cntr_dicts_orgby_cy[key] = sorted(
                merged_id_cntr_dicts_orgby_cy[key], key=lambda item: item['cx'])

        # 把每排染色体编号字符x坐标距离小于等于ID_CHAR_X_TOLERANCE的只保留一个
        for key, cntr_dicts in merged_id_cntr_dicts_orgby_cy.items():
            pre_cx = None
            merged = []
            # 保留第一个
            for cntr_dict in cntr_dicts:
                cur_cx = cntr_dict['cx']
                if pre_cx is None or abs(cur_cx - pre_cx) > ID_CHAR_X_TOLERANCE:
                    merged.append(cntr_dict)
                pre_cx = cur_cx
            merged_id_cntr_dicts_orgby_cy[key] = merged

        # 轮廓经过案列合并和按行合并后，检查每行染色体编号的轮廓数
        id_num_in_rows = [ROW_1_ID_NUM, ROW_2_ID_NUM, ROW_3_ID_NUM, ROW_4_ID_NUM]
        for idx, key in enumerate(merged_id_cntr_dicts_orgby_cy):
            if len(merged_id_cntr_dicts_orgby_cy[key]) != id_num_in_rows[idx]:
                raise ValueError(f'{self.img["fp"]}第{
                    idx+1}排染色体编号数量为{len(merged_id_cntr_dicts_orgby_cy[key])},应该为{id_num_in_rows[idx]}')

        # 汇总染色体编号信息
        chromo_id_list = ["1", "2", "3", "4", "5",
                          "6", "7", "8", "9", "10", "11", "12",
                          "13", "14", "15", "16", "17", "18",
                          "19", "20", "21", "22", "X", "Y"]
        chromo_idx = 0
        for cntr_dicts in merged_id_cntr_dicts_orgby_cy.values():
            for cntr in cntr_dicts:
                cntr['chromo_id'] = chromo_id_list[chromo_idx]
                cntr['chromo_idx'] = chromo_idx
                chromo_idx += 1

        # SAVE RESULT to CLASS INSTANCE MEMBER PROPERTY
        self.id_cntr_dicts_orgby_cy = merged_id_cntr_dicts_orgby_cy
        self.id_cntr_dicts = [merged_id_cntr_dicts_orgby_cy[key]
                                 for key in merged_id_cntr_dicts_orgby_cy]

    def read_karyotype(self):
        """从报告图中读取染色体数据
        """
        # get all external contours
        cntrs = find_external_contours(
            self.img['img'], BIN_THRESH)

        # get all contours info
        self.cntr_dicts = [{} for _ in range(len(cntrs))]
        for idx, cntr in enumerate(cntrs):
            self._gather_contours_dict(idx, cntr)
        # 从核型图中获取编号信息
        # After this call, self.id_cntr_dicts AND self.id_char_cntr_dicts is ready to use
        # AND self.id_cntr_dicts_orgby_cy AND self.id_char_cntr_dicts_orgby_cy is also ready to use
        self._id_info()

        # 获取染色体编号轮廓之外的轮廓
        # 先获取染色体编号轮廓的索引，然后用这些索引过滤掉所有轮廓，得到剩下的轮廓就是染色体轮廓
        id_char_cntrs_cntr_idx = []
        for id_char_cntrs in self.id_char_cntr_dicts:
            id_char_cntrs_cntr_idx.extend(
                cntr['cntr_idx'] for cntr in id_char_cntrs
            )
        # get left contours
        left_cntr_dicts = [
            cntr for cntr in self.cntr_dicts if cntr['cntr_idx'] not in id_char_cntrs_cntr_idx]

        # organize left contours info by cy
        left_cntr_dicts_orgby_cy = {}
        cy_keys = list(self.id_cntr_dicts_orgby_cy.keys())
        for cntr in left_cntr_dicts:
            top_y_limit = 0
            bottom_y_limit = cy_keys[0]
            for cy in cy_keys:
                bottom_y_limit = cy
                if cntr['cy'] > top_y_limit and cntr['cy'] < bottom_y_limit:
                    if bottom_y_limit not in left_cntr_dicts_orgby_cy:
                        left_cntr_dicts_orgby_cy[bottom_y_limit] = []
                    left_cntr_dicts_orgby_cy[bottom_y_limit].append(cntr)
                    break
                top_y_limit = bottom_y_limit
        # sort left contours dict by cx
        for key in left_cntr_dicts_orgby_cy:
            left_cntr_dicts_orgby_cy[key] = sorted(
                left_cntr_dicts_orgby_cy[key], key=lambda item: item['cx'])

        # match left contours with chromo id
        # with same row key: cy, match left contours with id contours
        # the contour in left contours belong to the nearest id contour
        for cy_key, same_cy_left_cntr_dicts in left_cntr_dicts_orgby_cy.items():
            for left_cnt in same_cy_left_cntr_dicts:
                min_distance = float('inf')
                chromo_id = None
                chromo_idx = None
                for id_cnt in self.id_cntr_dicts_orgby_cy[cy_key]:
                    left_cntr_center = np.array(
                        left_cnt['center'], dtype=np.int32)
                    id_cntr_center = np.array(id_cnt['center'], dtype=np.int32)
                    distance = np.linalg.norm(left_cntr_center - id_cntr_center)
                    if distance < min_distance:
                        min_distance = distance
                        chromo_id = id_cnt['chromo_id']
                        chromo_idx = id_cnt['chromo_idx']
                left_cnt['chromo_id'] = chromo_id
                left_cnt['chromo_idx'] = chromo_idx
                left_cnt['distance_to_id'] = min_distance

        # NOW, ALL left contours have matched chromo id
        # Merge small pieces contours to near big contours
        # record small piece contour idx which need to be deleted after merge to main branch contour
        small_cnts_need_delete = []
        # The top loop is for each row
        for same_cy_left_cntr_dicts in left_cntr_dicts_orgby_cy.values():
            # 获取当前行所有染色体编号
            chromo_id_list = [ cntr['chromo_id'] for cntr in same_cy_left_cntr_dicts ]
            unq_chromo_id_list = list(set(chromo_id_list))

            # The 2nd level loop is for each left contours in same row
            # 按照染色体编号来判断相同编号的染色体中是否有小碎片需要合并
            for chromo_id in unq_chromo_id_list:
                same_chromo_id_cnts_dict = [ cntr for cntr in same_cy_left_cntr_dicts if cntr['chromo_id'] == chromo_id ]

                if len(same_chromo_id_cnts_dict) <= 1:
                    # Only ONE, no need to merge
                    continue

                max_area = max(cntr['area'] for cntr in same_chromo_id_cnts_dict)
                min_area = min(cntr['area'] for cntr in same_chromo_id_cnts_dict)

                if min_area / max_area > SMALL_PIECE_AREA_RATIO:
                    # Small piece is not small enough, which can be regarded as
                    # small piece from main branch. So no need to merge
                    continue

                small_piece_cntrs_dict = [ cntr for cntr in same_chromo_id_cnts_dict if cntr['area'] / max_area < SMALL_PIECE_AREA_RATIO ]
                main_branch_cntrs_dict = [ cntr for cntr in same_chromo_id_cnts_dict if cntr['area'] / max_area >= SMALL_PIECE_AREA_RATIO ]

                # for every small piece contour, find the nearest main branch contour
                for small_piece_cntr_dict in small_piece_cntrs_dict:
                    # 记录当轮廓间距离最小时,当时的距离
                    min_distance = float('inf')
                    # 同小碎片距离最近的主干轮廓
                    nearest_main_branch_cntr_dict = None
                    # 小碎片上距离主干轮廓最近点的索引
                    small_cntr_npi = None
                    # 主干轮廓上距离小碎片轮廓最近点的索引
                    main_cntr_npi = None
                    # 对主干轮廓进行循环,找到距离最近的主干轮廓
                    for main_branch_cntr_dict in main_branch_cntrs_dict:
                        distance, cntr_npi1, cntr_npi2 = get_distance_between_two_contours(small_piece_cntr_dict['cntr'], main_branch_cntr_dict['cntr'])
                        if distance < min_distance:
                            min_distance = distance
                            nearest_main_branch_cntr_dict = main_branch_cntr_dict
                            small_cntr_npi = cntr_npi1
                            main_cntr_npi = cntr_npi2
                    # 找到了每个小碎片最近的主干轮廓,以及最近点的索引
                    # 合并小碎片和主干轮廓
                    merged_cnt = merge_two_contours_by_npi(small_piece_cntr_dict['cntr'], nearest_main_branch_cntr_dict['cntr'], small_cntr_npi, main_cntr_npi)

                    # update merged contour info to nearest_main_branch_cntr_dict
                    nearest_main_branch_cntr_dict['cntr'] = merged_cnt
                    nearest_main_branch_cntr_dict['area'] = cv2.contourArea(merged_cnt)
                    nearest_main_branch_cntr_dict['rect'] = cv2.boundingRect(merged_cnt)
                    nearest_main_branch_cntr_dict['min_area_rect'] = cv2.minAreaRect(merged_cnt)
                    moments = cv2.moments(merged_cnt)
                    nearest_main_branch_cntr_dict['cx'] = int(moments['m10'] / moments['m00'])
                    nearest_main_branch_cntr_dict['cy'] = int(moments['m01'] / moments['m00'])
                    nearest_main_branch_cntr_dict['center'] = (nearest_main_branch_cntr_dict['cx'], nearest_main_branch_cntr_dict['cy'])

                    # 记录处理完成后，需要删除小碎片轮廓
                    small_cnts_need_delete.append(small_piece_cntr_dict['cntr_idx'])


        # 所有cy行的小碎片轮廓合并完成后,删除小碎片轮廓
        for same_cy_left_cntr_dicts in left_cntr_dicts_orgby_cy.values():
            cnts_idx_need_delete = [
                idx
                for idx, cntr in enumerate(same_cy_left_cntr_dicts)
                if cntr['cntr_idx'] in small_cnts_need_delete
            ]
            for idx in sorted(cnts_idx_need_delete, reverse=True):
                del same_cy_left_cntr_dicts[idx]

        # 到这里left_cntr_dicts_orgby_cy中就包括我们需要的所有数据了
        # 1. 每排的每个染色体轮廓都有染色体编号信息
        # 2. 每排的每个染色体碎片轮廓都同其染色体主干轮廓合并了
        # 3. 数据的排列格式是以cy为key的字典,每个cy对应的value是该cy行的所有的染色体轮廓信息
        #    类似于: {cy1:[{chromo_id:'1',chromo_idx:0,cx:100,cy:200,contour:[[x,y]]},...], cy2:[...], ...}
        self.chromo_cntr_dicts_orgby_cy = left_cntr_dicts_orgby_cy
        self.chromo_cntr_dicts = [ left_cntr_dicts_orgby_cy[key] for key in left_cntr_dicts_orgby_cy ]


    # Gather contour info for contours list
    def _gather_contours_dict(self, idx, contour):
        self.cntr_dicts[idx]['cntr_idx'] = idx
        self.cntr_dicts[idx]['cntr'] = contour
        self.cntr_dicts[idx]['area'] = cv2.contourArea(contour)
        self.cntr_dicts[idx]['rect'] = cv2.boundingRect(contour)
        self.cntr_dicts[idx]['min_area_rect'] = cv2.minAreaRect(contour)
        moments = cv2.moments(contour)
        if moments['m00'] != 0:
            self.cntr_dicts[idx]['cx'] = int(moments['m10'] / moments['m00'])
            self.cntr_dicts[idx]['cy'] = int(moments['m01'] / moments['m00'])
        else:
            ((cx, cy), (_,_), _) = cv2.minAreaRect(contour)
            self.cntr_dicts[idx]['cx'] = int(cx)
            self.cntr_dicts[idx]['cy'] = int(cy)
        self.cntr_dicts[idx]['center'] = (self.cntr_dicts[idx]['cx'], self.cntr_dicts[idx]['cy'])
