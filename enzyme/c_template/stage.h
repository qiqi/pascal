static void ${STAGE_NAME}(PointStruct2D *p)
{
    double * source    = p->C_input;
    double * source_ip = p->E_input;
    double * source_im = p->W_input;
    double * source_jp = p->S_input;
    double * source_jm = p->N_input;
    double * source_kp = p->S_input;
    double * source_km = p->N_input;
    double * sink      = p->output;
    double * constants = p->C_constants;

    ${CODE}
}
