static void init(int i,int j,InitPoint2D *p)
{

    double * source    = p->U_input;
    double * source_ip = p->U_input;
    double * source_im = p->U_input;
    double * source_jp = p->U_input;
    double * source_jm = p->U_input;
    double * source_kp = p->U_input;
    double * source_km = p->U_input;
    double * sink      = p->U_input;
    double * constants = p->U_constants;

const double triburary_0[1] = {i};
const double triburary_0_ip[1] = {i};
const double triburary_0_im[1] = {i};
const double triburary_0_jp[1] = {i};
const double triburary_0_jm[1] = {i};
const double triburary_0_km[1] = {i};
const double triburary_0_kp[1] = {i};
const double triburary_1[1] = {j};
const double triburary_1_ip[1] = {j};
const double triburary_1_im[1] = {j};
const double triburary_1_jp[1] = {j};
const double triburary_1_jm[1] = {j};
const double triburary_1_km[1] = {j};
const double triburary_1_kp[1] = {j};

double var_0[1];
var_0[0] = 1.08481761983;

double var_1[6];
var_1[0] = source[0];
var_1[1] = source[1];
var_1[2] = source[2];
var_1[3] = source[3];
var_1[4] = source[4];
var_1[5] = source[5];

var_1[0] = var_0[0];

double var_1_im[6];
var_1_im[0] = source_im[0];
var_1_im[1] = source_im[1];
var_1_im[2] = source_im[2];
var_1_im[3] = source_im[3];
var_1_im[4] = source_im[4];
var_1_im[5] = source_im[5];

var_1_im[0] = var_0[0];

double var_1_ip[6];
var_1_ip[0] = source_ip[0];
var_1_ip[1] = source_ip[1];
var_1_ip[2] = source_ip[2];
var_1_ip[3] = source_ip[3];
var_1_ip[4] = source_ip[4];
var_1_ip[5] = source_ip[5];

var_1_ip[0] = var_0[0];

double var_1_jm[6];
var_1_jm[0] = source_jm[0];
var_1_jm[1] = source_jm[1];
var_1_jm[2] = source_jm[2];
var_1_jm[3] = source_jm[3];
var_1_jm[4] = source_jm[4];
var_1_jm[5] = source_jm[5];

var_1_jm[0] = var_0[0];

double var_1_jp[6];
var_1_jp[0] = source_jp[0];
var_1_jp[1] = source_jp[1];
var_1_jp[2] = source_jp[2];
var_1_jp[3] = source_jp[3];
var_1_jp[4] = source_jp[4];
var_1_jp[5] = source_jp[5];

var_1_jp[0] = var_0[0];

double var_1_km[6];
var_1_km[0] = source_km[0];
var_1_km[1] = source_km[1];
var_1_km[2] = source_km[2];
var_1_km[3] = source_km[3];
var_1_km[4] = source_km[4];
var_1_km[5] = source_km[5];

var_1_km[0] = var_0[0];

double var_1_kp[6];
var_1_kp[0] = source_kp[0];
var_1_kp[1] = source_kp[1];
var_1_kp[2] = source_kp[2];
var_1_kp[3] = source_kp[3];
var_1_kp[4] = source_kp[4];
var_1_kp[5] = source_kp[5];

var_1_kp[0] = var_0[0];

double var_2[1];
var_2[0] = 0.5;

double var_3[1];
var_3[0] = triburary_0[0] + var_2[0];

double var_3_im[1];
var_3_im[0] = triburary_0_im[0] + var_2[0];

double var_3_ip[1];
var_3_ip[0] = triburary_0_ip[0] + var_2[0];

double var_3_jm[1];
var_3_jm[0] = triburary_0_jm[0] + var_2[0];

double var_3_jp[1];
var_3_jp[0] = triburary_0_jp[0] + var_2[0];

double var_3_km[1];
var_3_km[0] = triburary_0_km[0] + var_2[0];

double var_3_kp[1];
var_3_kp[0] = triburary_0_kp[0] + var_2[0];

double var_4[1];
var_4[0] = 0.5;

double var_5[1];
var_5[0] = triburary_1[0] + var_4[0];

double var_5_im[1];
var_5_im[0] = triburary_1_im[0] + var_4[0];

double var_5_ip[1];
var_5_ip[0] = triburary_1_ip[0] + var_4[0];

double var_5_jm[1];
var_5_jm[0] = triburary_1_jm[0] + var_4[0];

double var_5_jp[1];
var_5_jp[0] = triburary_1_jp[0] + var_4[0];

double var_5_km[1];
var_5_km[0] = triburary_1_km[0] + var_4[0];

double var_5_kp[1];
var_5_kp[0] = triburary_1_kp[0] + var_4[0];

double var_6[1];
var_6[0] = 94.1591073662;

double var_7[6];
var_7[0] = var_1[0];
var_7[1] = var_1[1];
var_7[2] = var_1[2];
var_7[3] = var_1[3];
var_7[4] = var_1[4];
var_7[5] = var_1[5];

var_7[1] = var_6[0];

double var_7_im[6];
var_7_im[0] = var_1_im[0];
var_7_im[1] = var_1_im[1];
var_7_im[2] = var_1_im[2];
var_7_im[3] = var_1_im[3];
var_7_im[4] = var_1_im[4];
var_7_im[5] = var_1_im[5];

var_7_im[1] = var_6[0];

double var_7_ip[6];
var_7_ip[0] = var_1_ip[0];
var_7_ip[1] = var_1_ip[1];
var_7_ip[2] = var_1_ip[2];
var_7_ip[3] = var_1_ip[3];
var_7_ip[4] = var_1_ip[4];
var_7_ip[5] = var_1_ip[5];

var_7_ip[1] = var_6[0];

double var_7_jm[6];
var_7_jm[0] = var_1_jm[0];
var_7_jm[1] = var_1_jm[1];
var_7_jm[2] = var_1_jm[2];
var_7_jm[3] = var_1_jm[3];
var_7_jm[4] = var_1_jm[4];
var_7_jm[5] = var_1_jm[5];

var_7_jm[1] = var_6[0];

double var_7_jp[6];
var_7_jp[0] = var_1_jp[0];
var_7_jp[1] = var_1_jp[1];
var_7_jp[2] = var_1_jp[2];
var_7_jp[3] = var_1_jp[3];
var_7_jp[4] = var_1_jp[4];
var_7_jp[5] = var_1_jp[5];

var_7_jp[1] = var_6[0];

double var_7_km[6];
var_7_km[0] = var_1_km[0];
var_7_km[1] = var_1_km[1];
var_7_km[2] = var_1_km[2];
var_7_km[3] = var_1_km[3];
var_7_km[4] = var_1_km[4];
var_7_km[5] = var_1_km[5];

var_7_km[1] = var_6[0];

double var_7_kp[6];
var_7_kp[0] = var_1_kp[0];
var_7_kp[1] = var_1_kp[1];
var_7_kp[2] = var_1_kp[2];
var_7_kp[3] = var_1_kp[3];
var_7_kp[4] = var_1_kp[4];
var_7_kp[5] = var_1_kp[5];

var_7_kp[1] = var_6[0];

double var_8[1];
var_8[0] = 0.05;

double var_9[1];
var_9[0] = var_3[0] * var_8[0];

double var_9_im[1];
var_9_im[0] = var_3_im[0] * var_8[0];

double var_9_ip[1];
var_9_ip[0] = var_3_ip[0] * var_8[0];

double var_9_jm[1];
var_9_jm[0] = var_3_jm[0] * var_8[0];

double var_9_jp[1];
var_9_jp[0] = var_3_jp[0] * var_8[0];

double var_9_km[1];
var_9_km[0] = var_3_km[0] * var_8[0];

double var_9_kp[1];
var_9_kp[0] = var_3_kp[0] * var_8[0];

double var_10[1];
var_10[0] = 0.05;

double var_11[1];
var_11[0] = var_5[0] * var_10[0];

double var_11_im[1];
var_11_im[0] = var_5_im[0] * var_10[0];

double var_11_ip[1];
var_11_ip[0] = var_5_ip[0] * var_10[0];

double var_11_jm[1];
var_11_jm[0] = var_5_jm[0] * var_10[0];

double var_11_jp[1];
var_11_jp[0] = var_5_jp[0] * var_10[0];

double var_11_km[1];
var_11_km[0] = var_5_km[0] * var_10[0];

double var_11_kp[1];
var_11_kp[0] = var_5_kp[0] * var_10[0];

double var_12[1];
var_12[0] = 0.0;

double var_13[6];
var_13[0] = var_7[0];
var_13[1] = var_7[1];
var_13[2] = var_7[2];
var_13[3] = var_7[3];
var_13[4] = var_7[4];
var_13[5] = var_7[5];

var_13[2] = var_12[0];

double var_13_im[6];
var_13_im[0] = var_7_im[0];
var_13_im[1] = var_7_im[1];
var_13_im[2] = var_7_im[2];
var_13_im[3] = var_7_im[3];
var_13_im[4] = var_7_im[4];
var_13_im[5] = var_7_im[5];

var_13_im[2] = var_12[0];

double var_13_ip[6];
var_13_ip[0] = var_7_ip[0];
var_13_ip[1] = var_7_ip[1];
var_13_ip[2] = var_7_ip[2];
var_13_ip[3] = var_7_ip[3];
var_13_ip[4] = var_7_ip[4];
var_13_ip[5] = var_7_ip[5];

var_13_ip[2] = var_12[0];

double var_13_jm[6];
var_13_jm[0] = var_7_jm[0];
var_13_jm[1] = var_7_jm[1];
var_13_jm[2] = var_7_jm[2];
var_13_jm[3] = var_7_jm[3];
var_13_jm[4] = var_7_jm[4];
var_13_jm[5] = var_7_jm[5];

var_13_jm[2] = var_12[0];

double var_13_jp[6];
var_13_jp[0] = var_7_jp[0];
var_13_jp[1] = var_7_jp[1];
var_13_jp[2] = var_7_jp[2];
var_13_jp[3] = var_7_jp[3];
var_13_jp[4] = var_7_jp[4];
var_13_jp[5] = var_7_jp[5];

var_13_jp[2] = var_12[0];

double var_13_km[6];
var_13_km[0] = var_7_km[0];
var_13_km[1] = var_7_km[1];
var_13_km[2] = var_7_km[2];
var_13_km[3] = var_7_km[3];
var_13_km[4] = var_7_km[4];
var_13_km[5] = var_7_km[5];

var_13_km[2] = var_12[0];

double var_13_kp[6];
var_13_kp[0] = var_7_kp[0];
var_13_kp[1] = var_7_kp[1];
var_13_kp[2] = var_7_kp[2];
var_13_kp[3] = var_7_kp[3];
var_13_kp[4] = var_7_kp[4];
var_13_kp[5] = var_7_kp[5];

var_13_kp[2] = var_12[0];

double var_14[1];
var_14[0] = 2.56;

double var_15[1];
var_15[0] = var_9[0] - var_14[0];

double var_15_im[1];
var_15_im[0] = var_9_im[0] - var_14[0];

double var_15_ip[1];
var_15_ip[0] = var_9_ip[0] - var_14[0];

double var_15_jm[1];
var_15_jm[0] = var_9_jm[0] - var_14[0];

double var_15_jp[1];
var_15_jp[0] = var_9_jp[0] - var_14[0];

double var_15_km[1];
var_15_km[0] = var_9_km[0] - var_14[0];

double var_15_kp[1];
var_15_kp[0] = var_9_kp[0] - var_14[0];

double var_16[1];
var_16[0] = 3.2;

double var_17[1];
var_17[0] = var_11[0] - var_16[0];

double var_17_im[1];
var_17_im[0] = var_11_im[0] - var_16[0];

double var_17_ip[1];
var_17_ip[0] = var_11_ip[0] - var_16[0];

double var_17_jm[1];
var_17_jm[0] = var_11_jm[0] - var_16[0];

double var_17_jp[1];
var_17_jp[0] = var_11_jp[0] - var_16[0];

double var_17_km[1];
var_17_km[0] = var_11_km[0] - var_16[0];

double var_17_kp[1];
var_17_kp[0] = var_11_kp[0] - var_16[0];

double var_18[1];
var_18[0] = 12.8;

double var_19[1];
var_19[0] = var_15[0] / var_18[0];

double var_19_im[1];
var_19_im[0] = var_15_im[0] / var_18[0];

double var_19_ip[1];
var_19_ip[0] = var_15_ip[0] / var_18[0];

double var_19_jm[1];
var_19_jm[0] = var_15_jm[0] / var_18[0];

double var_19_jp[1];
var_19_jp[0] = var_15_jp[0] / var_18[0];

double var_19_km[1];
var_19_km[0] = var_15_km[0] / var_18[0];

double var_19_kp[1];
var_19_kp[0] = var_15_kp[0] / var_18[0];

double var_20[1];
var_20[0] = 6.4;

double var_21[1];
var_21[0] = var_17[0] / var_20[0];

double var_21_im[1];
var_21_im[0] = var_17_im[0] / var_20[0];

double var_21_ip[1];
var_21_ip[0] = var_17_ip[0] / var_20[0];

double var_21_jm[1];
var_21_jm[0] = var_17_jm[0] / var_20[0];

double var_21_jp[1];
var_21_jp[0] = var_17_jp[0] / var_20[0];

double var_21_km[1];
var_21_km[0] = var_17_km[0] / var_20[0];

double var_21_kp[1];
var_21_kp[0] = var_17_kp[0] / var_20[0];

double var_22[1];
var_22[0] = 101325.0;

double var_23[6];
var_23[0] = var_13[0];
var_23[1] = var_13[1];
var_23[2] = var_13[2];
var_23[3] = var_13[3];
var_23[4] = var_13[4];
var_23[5] = var_13[5];

var_23[3] = var_22[0];

double var_23_im[6];
var_23_im[0] = var_13_im[0];
var_23_im[1] = var_13_im[1];
var_23_im[2] = var_13_im[2];
var_23_im[3] = var_13_im[3];
var_23_im[4] = var_13_im[4];
var_23_im[5] = var_13_im[5];

var_23_im[3] = var_22[0];

double var_23_ip[6];
var_23_ip[0] = var_13_ip[0];
var_23_ip[1] = var_13_ip[1];
var_23_ip[2] = var_13_ip[2];
var_23_ip[3] = var_13_ip[3];
var_23_ip[4] = var_13_ip[4];
var_23_ip[5] = var_13_ip[5];

var_23_ip[3] = var_22[0];

double var_23_jm[6];
var_23_jm[0] = var_13_jm[0];
var_23_jm[1] = var_13_jm[1];
var_23_jm[2] = var_13_jm[2];
var_23_jm[3] = var_13_jm[3];
var_23_jm[4] = var_13_jm[4];
var_23_jm[5] = var_13_jm[5];

var_23_jm[3] = var_22[0];

double var_23_jp[6];
var_23_jp[0] = var_13_jp[0];
var_23_jp[1] = var_13_jp[1];
var_23_jp[2] = var_13_jp[2];
var_23_jp[3] = var_13_jp[3];
var_23_jp[4] = var_13_jp[4];
var_23_jp[5] = var_13_jp[5];

var_23_jp[3] = var_22[0];

double var_23_km[6];
var_23_km[0] = var_13_km[0];
var_23_km[1] = var_13_km[1];
var_23_km[2] = var_13_km[2];
var_23_km[3] = var_13_km[3];
var_23_km[4] = var_13_km[4];
var_23_km[5] = var_13_km[5];

var_23_km[3] = var_22[0];

double var_23_kp[6];
var_23_kp[0] = var_13_kp[0];
var_23_kp[1] = var_13_kp[1];
var_23_kp[2] = var_13_kp[2];
var_23_kp[3] = var_13_kp[3];
var_23_kp[4] = var_13_kp[4];
var_23_kp[5] = var_13_kp[5];

var_23_kp[3] = var_22[0];

double var_24[1];
var_24[0] = var_15[0] * var_15[0];

double var_24_im[1];
var_24_im[0] = var_15_im[0] * var_15_im[0];

double var_24_ip[1];
var_24_ip[0] = var_15_ip[0] * var_15_ip[0];

double var_24_jm[1];
var_24_jm[0] = var_15_jm[0] * var_15_jm[0];

double var_24_jp[1];
var_24_jp[0] = var_15_jp[0] * var_15_jp[0];

double var_24_km[1];
var_24_km[0] = var_15_km[0] * var_15_km[0];

double var_24_kp[1];
var_24_kp[0] = var_15_kp[0] * var_15_kp[0];

double var_25[1];
var_25[0] = 0.25;

double var_26[1];
var_26[0] = var_17[0] - var_25[0];

double var_26_im[1];
var_26_im[0] = var_17_im[0] - var_25[0];

double var_26_ip[1];
var_26_ip[0] = var_17_ip[0] - var_25[0];

double var_26_jm[1];
var_26_jm[0] = var_17_jm[0] - var_25[0];

double var_26_jp[1];
var_26_jp[0] = var_17_jp[0] - var_25[0];

double var_26_km[1];
var_26_km[0] = var_17_km[0] - var_25[0];

double var_26_kp[1];
var_26_kp[0] = var_17_kp[0] - var_25[0];

double var_27[1];
var_27[0] = 0.2;

double var_28[1];
var_28[0] = var_19[0] + var_27[0];

double var_28_im[1];
var_28_im[0] = var_19_im[0] + var_27[0];

double var_28_ip[1];
var_28_ip[0] = var_19_ip[0] + var_27[0];

double var_28_jm[1];
var_28_jm[0] = var_19_jm[0] + var_27[0];

double var_28_jp[1];
var_28_jp[0] = var_19_jp[0] + var_27[0];

double var_28_km[1];
var_28_km[0] = var_19_km[0] + var_27[0];

double var_28_kp[1];
var_28_kp[0] = var_19_kp[0] + var_27[0];

double var_29[1];
var_29[0] = 3.14159265359;

double var_30[1];
var_30[0] = var_21[0] * var_29[0];

double var_30_im[1];
var_30_im[0] = var_21_im[0] * var_29[0];

double var_30_ip[1];
var_30_ip[0] = var_21_ip[0] * var_29[0];

double var_30_jm[1];
var_30_jm[0] = var_21_jm[0] * var_29[0];

double var_30_jp[1];
var_30_jp[0] = var_21_jp[0] * var_29[0];

double var_30_km[1];
var_30_km[0] = var_21_km[0] * var_29[0];

double var_30_kp[1];
var_30_kp[0] = var_21_kp[0] * var_29[0];

double var_31[1];
var_31[0] = 0.25;

double var_32[1];
var_32[0] = var_17[0] - var_31[0];

double var_32_im[1];
var_32_im[0] = var_17_im[0] - var_31[0];

double var_32_ip[1];
var_32_ip[0] = var_17_ip[0] - var_31[0];

double var_32_jm[1];
var_32_jm[0] = var_17_jm[0] - var_31[0];

double var_32_jp[1];
var_32_jp[0] = var_17_jp[0] - var_31[0];

double var_32_km[1];
var_32_km[0] = var_17_km[0] - var_31[0];

double var_32_kp[1];
var_32_kp[0] = var_17_kp[0] - var_31[0];

double var_33[1];
var_33[0] = 3.14159265359;

double var_34[1];
var_34[0] = var_28[0] * var_33[0];

double var_34_im[1];
var_34_im[0] = var_28_im[0] * var_33[0];

double var_34_ip[1];
var_34_ip[0] = var_28_ip[0] * var_33[0];

double var_34_jm[1];
var_34_jm[0] = var_28_jm[0] * var_33[0];

double var_34_jp[1];
var_34_jp[0] = var_28_jp[0] * var_33[0];

double var_34_km[1];
var_34_km[0] = var_28_km[0] * var_33[0];

double var_34_kp[1];
var_34_kp[0] = var_28_kp[0] * var_33[0];

double var_35[1];
var_35[0] = sin(var_30[0]);

double var_35_im[1];
var_35_im[0] = sin(var_30_im[0]);

double var_35_ip[1];
var_35_ip[0] = sin(var_30_ip[0]);

double var_35_jm[1];
var_35_jm[0] = sin(var_30_jm[0]);

double var_35_jp[1];
var_35_jp[0] = sin(var_30_jp[0]);

double var_35_km[1];
var_35_km[0] = sin(var_30_km[0]);

double var_35_kp[1];
var_35_kp[0] = sin(var_30_kp[0]);

double var_36[1];
var_36[0] = var_26[0] * var_32[0];

double var_36_im[1];
var_36_im[0] = var_26_im[0] * var_32_im[0];

double var_36_ip[1];
var_36_ip[0] = var_26_ip[0] * var_32_ip[0];

double var_36_jm[1];
var_36_jm[0] = var_26_jm[0] * var_32_jm[0];

double var_36_jp[1];
var_36_jp[0] = var_26_jp[0] * var_32_jp[0];

double var_36_km[1];
var_36_km[0] = var_26_km[0] * var_32_km[0];

double var_36_kp[1];
var_36_kp[0] = var_26_kp[0] * var_32_kp[0];

double var_37[1];
var_37[0] = cos(var_34[0]);

double var_37_im[1];
var_37_im[0] = cos(var_34_im[0]);

double var_37_ip[1];
var_37_ip[0] = cos(var_34_ip[0]);

double var_37_jm[1];
var_37_jm[0] = cos(var_34_jm[0]);

double var_37_jp[1];
var_37_jp[0] = cos(var_34_jp[0]);

double var_37_km[1];
var_37_km[0] = cos(var_34_km[0]);

double var_37_kp[1];
var_37_kp[0] = cos(var_34_kp[0]);

double var_38[1];
var_38[0] = 0.1;

double var_39[1];
var_39[0] = var_36[0] / var_38[0];

double var_39_im[1];
var_39_im[0] = var_36_im[0] / var_38[0];

double var_39_ip[1];
var_39_ip[0] = var_36_ip[0] / var_38[0];

double var_39_jm[1];
var_39_jm[0] = var_36_jm[0] / var_38[0];

double var_39_jp[1];
var_39_jp[0] = var_36_jp[0] / var_38[0];

double var_39_km[1];
var_39_km[0] = var_36_km[0] / var_38[0];

double var_39_kp[1];
var_39_kp[0] = var_36_kp[0] / var_38[0];

double var_40[1];
var_40[0] = 64.0;

double var_41[1];
var_41[0] = pow(var_37[0], var_40[0]);

double var_41_im[1];
var_41_im[0] = pow(var_37_im[0], var_40[0]);

double var_41_ip[1];
var_41_ip[0] = pow(var_37_ip[0], var_40[0]);

double var_41_jm[1];
var_41_jm[0] = pow(var_37_jm[0], var_40[0]);

double var_41_jp[1];
var_41_jp[0] = pow(var_37_jp[0], var_40[0]);

double var_41_km[1];
var_41_km[0] = pow(var_37_km[0], var_40[0]);

double var_41_kp[1];
var_41_kp[0] = pow(var_37_kp[0], var_40[0]);

double var_42[1];
var_42[0] = var_24[0] + var_39[0];

double var_42_im[1];
var_42_im[0] = var_24_im[0] + var_39_im[0];

double var_42_ip[1];
var_42_ip[0] = var_24_ip[0] + var_39_ip[0];

double var_42_jm[1];
var_42_jm[0] = var_24_jm[0] + var_39_jm[0];

double var_42_jp[1];
var_42_jp[0] = var_24_jp[0] + var_39_jp[0];

double var_42_km[1];
var_42_km[0] = var_24_km[0] + var_39_km[0];

double var_42_kp[1];
var_42_kp[0] = var_24_kp[0] + var_39_kp[0];

double var_43[1];
var_43[0] = 64.0;

double var_44[1];
var_44[0] = pow(var_35[0], var_43[0]);

double var_44_im[1];
var_44_im[0] = pow(var_35_im[0], var_43[0]);

double var_44_ip[1];
var_44_ip[0] = pow(var_35_ip[0], var_43[0]);

double var_44_jm[1];
var_44_jm[0] = pow(var_35_jm[0], var_43[0]);

double var_44_jp[1];
var_44_jp[0] = pow(var_35_jp[0], var_43[0]);

double var_44_km[1];
var_44_km[0] = pow(var_35_km[0], var_43[0]);

double var_44_kp[1];
var_44_kp[0] = pow(var_35_kp[0], var_43[0]);

double var_45[1];
var_45[0] = 8.0;

double var_46[1];
var_46[0] = pow(var_42[0], var_45[0]);

double var_46_im[1];
var_46_im[0] = pow(var_42_im[0], var_45[0]);

double var_46_ip[1];
var_46_ip[0] = pow(var_42_ip[0], var_45[0]);

double var_46_jm[1];
var_46_jm[0] = pow(var_42_jm[0], var_45[0]);

double var_46_jp[1];
var_46_jp[0] = pow(var_42_jp[0], var_45[0]);

double var_46_km[1];
var_46_km[0] = pow(var_42_km[0], var_45[0]);

double var_46_kp[1];
var_46_kp[0] = pow(var_42_kp[0], var_45[0]);

double var_47[1];
var_47[0] = var_41[0] + var_44[0];

double var_47_im[1];
var_47_im[0] = var_41_im[0] + var_44_im[0];

double var_47_ip[1];
var_47_ip[0] = var_41_ip[0] + var_44_ip[0];

double var_47_jm[1];
var_47_jm[0] = var_41_jm[0] + var_44_jm[0];

double var_47_jp[1];
var_47_jp[0] = var_41_jp[0] + var_44_jp[0];

double var_47_km[1];
var_47_km[0] = var_41_km[0] + var_44_km[0];

double var_47_kp[1];
var_47_kp[0] = var_41_kp[0] + var_44_kp[0];

double var_48[1];
var_48[0] = -(var_46[0]);

double var_48_im[1];
var_48_im[0] = -(var_46_im[0]);

double var_48_ip[1];
var_48_ip[0] = -(var_46_ip[0]);

double var_48_jm[1];
var_48_jm[0] = -(var_46_jm[0]);

double var_48_jp[1];
var_48_jp[0] = -(var_46_jp[0]);

double var_48_km[1];
var_48_km[0] = -(var_46_km[0]);

double var_48_kp[1];
var_48_kp[0] = -(var_46_kp[0]);

double var_49[1];
var_49[0] = exp(var_48[0]);

double var_49_im[1];
var_49_im[0] = exp(var_48_im[0]);

double var_49_ip[1];
var_49_ip[0] = exp(var_48_ip[0]);

double var_49_jm[1];
var_49_jm[0] = exp(var_48_jm[0]);

double var_49_jp[1];
var_49_jp[0] = exp(var_48_jp[0]);

double var_49_km[1];
var_49_km[0] = exp(var_48_km[0]);

double var_49_kp[1];
var_49_kp[0] = exp(var_48_kp[0]);

double var_50[6];
var_50[0] = var_23[0];
var_50[1] = var_23[1];
var_50[2] = var_23[2];
var_50[3] = var_23[3];
var_50[4] = var_23[4];
var_50[5] = var_23[5];

var_50[4] = var_49[0];

double var_50_im[6];
var_50_im[0] = var_23_im[0];
var_50_im[1] = var_23_im[1];
var_50_im[2] = var_23_im[2];
var_50_im[3] = var_23_im[3];
var_50_im[4] = var_23_im[4];
var_50_im[5] = var_23_im[5];

var_50_im[4] = var_49_im[0];

double var_50_ip[6];
var_50_ip[0] = var_23_ip[0];
var_50_ip[1] = var_23_ip[1];
var_50_ip[2] = var_23_ip[2];
var_50_ip[3] = var_23_ip[3];
var_50_ip[4] = var_23_ip[4];
var_50_ip[5] = var_23_ip[5];

var_50_ip[4] = var_49_ip[0];

double var_50_jm[6];
var_50_jm[0] = var_23_jm[0];
var_50_jm[1] = var_23_jm[1];
var_50_jm[2] = var_23_jm[2];
var_50_jm[3] = var_23_jm[3];
var_50_jm[4] = var_23_jm[4];
var_50_jm[5] = var_23_jm[5];

var_50_jm[4] = var_49_jm[0];

double var_50_jp[6];
var_50_jp[0] = var_23_jp[0];
var_50_jp[1] = var_23_jp[1];
var_50_jp[2] = var_23_jp[2];
var_50_jp[3] = var_23_jp[3];
var_50_jp[4] = var_23_jp[4];
var_50_jp[5] = var_23_jp[5];

var_50_jp[4] = var_49_jp[0];

double var_50_km[6];
var_50_km[0] = var_23_km[0];
var_50_km[1] = var_23_km[1];
var_50_km[2] = var_23_km[2];
var_50_km[3] = var_23_km[3];
var_50_km[4] = var_23_km[4];
var_50_km[5] = var_23_km[5];

var_50_km[4] = var_49_km[0];

double var_50_kp[6];
var_50_kp[0] = var_23_kp[0];
var_50_kp[1] = var_23_kp[1];
var_50_kp[2] = var_23_kp[2];
var_50_kp[3] = var_23_kp[3];
var_50_kp[4] = var_23_kp[4];
var_50_kp[5] = var_23_kp[5];

var_50_kp[4] = var_49_kp[0];

double var_51[1];
var_51[0] = 2.0;

double var_52[1];
var_52[0] = var_47[0] * var_51[0];

double var_52_im[1];
var_52_im[0] = var_47_im[0] * var_51[0];

double var_52_ip[1];
var_52_ip[0] = var_47_ip[0] * var_51[0];

double var_52_jm[1];
var_52_jm[0] = var_47_jm[0] * var_51[0];

double var_52_jp[1];
var_52_jp[0] = var_47_jp[0] * var_51[0];

double var_52_km[1];
var_52_km[0] = var_47_km[0] * var_51[0];

double var_52_kp[1];
var_52_kp[0] = var_47_kp[0] * var_51[0];

double var_53[6];
var_53[0] = var_50[0];
var_53[1] = var_50[1];
var_53[2] = var_50[2];
var_53[3] = var_50[3];
var_53[4] = var_50[4];
var_53[5] = var_50[5];

var_53[5] = var_52[0];

double var_53_im[6];
var_53_im[0] = var_50_im[0];
var_53_im[1] = var_50_im[1];
var_53_im[2] = var_50_im[2];
var_53_im[3] = var_50_im[3];
var_53_im[4] = var_50_im[4];
var_53_im[5] = var_50_im[5];

var_53_im[5] = var_52_im[0];

double var_53_ip[6];
var_53_ip[0] = var_50_ip[0];
var_53_ip[1] = var_50_ip[1];
var_53_ip[2] = var_50_ip[2];
var_53_ip[3] = var_50_ip[3];
var_53_ip[4] = var_50_ip[4];
var_53_ip[5] = var_50_ip[5];

var_53_ip[5] = var_52_ip[0];

double var_53_jm[6];
var_53_jm[0] = var_50_jm[0];
var_53_jm[1] = var_50_jm[1];
var_53_jm[2] = var_50_jm[2];
var_53_jm[3] = var_50_jm[3];
var_53_jm[4] = var_50_jm[4];
var_53_jm[5] = var_50_jm[5];

var_53_jm[5] = var_52_jm[0];

double var_53_jp[6];
var_53_jp[0] = var_50_jp[0];
var_53_jp[1] = var_50_jp[1];
var_53_jp[2] = var_50_jp[2];
var_53_jp[3] = var_50_jp[3];
var_53_jp[4] = var_50_jp[4];
var_53_jp[5] = var_50_jp[5];

var_53_jp[5] = var_52_jp[0];

double var_53_km[6];
var_53_km[0] = var_50_km[0];
var_53_km[1] = var_50_km[1];
var_53_km[2] = var_50_km[2];
var_53_km[3] = var_50_km[3];
var_53_km[4] = var_50_km[4];
var_53_km[5] = var_50_km[5];

var_53_km[5] = var_52_km[0];

double var_53_kp[6];
var_53_kp[0] = var_50_kp[0];
var_53_kp[1] = var_50_kp[1];
var_53_kp[2] = var_50_kp[2];
var_53_kp[3] = var_50_kp[3];
var_53_kp[4] = var_50_kp[4];
var_53_kp[5] = var_50_kp[5];

var_53_kp[5] = var_52_kp[0];

sink[0] = var_53[0];
sink[1] = var_53[1];
sink[2] = var_53[2];
sink[3] = var_53[3];
constants[0] = var_53[4];
constants[1] = var_53[5];


}

