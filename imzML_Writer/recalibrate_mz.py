import numpy as np

def recalibrate(mz:list,int:list,lock_mz:float,search_tol:float,ppm_off:float):
    """Performs a coarse m/z recalibration based on shifting a lock mass back to target, and everything else by the same ppm shift"""
    ##Ignore all if lock_mz is 0 and return the original array
    if lock_mz == 0:
        return mz, int
    else:
        ##Compute ppm error of every m/z in the spectrum to the lock mass     
        diff_mz_ppm = (mz - lock_mz)/lock_mz * 1e6

        ##Find candidate m/z within the tolerance window
        iter=-1
        candidate_mz =[]
        candidate_int = []
        for ppm_diff in diff_mz_ppm:
            iter += 1
            if abs(ppm_diff) <= search_tol:
                candidate_mz.append(mz[iter])
                candidate_int.append(int[iter])
        
        ##take the highest intensity peak in the tolerance window as the lock mass, and identify the correction ppm error based on it
        try:
            match_idx = np.where(candidate_int == max(candidate_int))[0][0]
            id_mz = candidate_mz[match_idx]
            ppm_off = (id_mz - lock_mz)/lock_mz * 1e6
        except:
            pass

        ##Compute recalibrated mass spectrum based on identified lock mass. If above failed (lock mass not identified within tolerance window)
        ##Than the spectrum is corrected based on input 'ppm_off' variable, typically whatever the correction was on the previous spectrum
        recalibrated_mz = mz - (ppm_off * mz / 1e6)
        return recalibrated_mz, ppm_off




    
