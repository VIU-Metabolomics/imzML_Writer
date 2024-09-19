import numpy as np

def recalibrate(mz,int,lock_mz,search_tol,ppm_off):

    if lock_mz == 0:
        return mz, int
    else:     
        diff_mz_ppm = (mz - lock_mz)/lock_mz * 1e6

        iter=-1
        candidate_mz =[]
        candidate_int = []
        for ppm_diff in diff_mz_ppm:
            iter += 1
            if abs(ppm_diff) <= search_tol:
                candidate_mz.append(mz[iter])
                candidate_int.append(int[iter])
        
        try:
            match_idx = np.where(candidate_int == max(candidate_int))[0][0]
            id_mz = candidate_mz[match_idx]
            ppm_off = (id_mz - lock_mz)/lock_mz * 1e6
        except:
            pass

        recalibrated_mz = mz - (ppm_off * mz / 1e6)
        return recalibrated_mz, ppm_off




    
