def _get_log_data(self, data_var, x, y):
    logdepth = [-999, -999]
    logdata = [0, 0]
    for t in range(len(self.data["dimen_t"])):
        data_t = self.data[data_var].sel(dimen_x=y, dimen_y=x, dimen_t=t).values
        depth_t = self.data["zcor"].sel(dimen_x=y, dimen_y=x, dimen_t=t).values
        if logdepth[-1] < depth_t:
            logdepth.append(float(logdepth[-1]))
            logdepth.append(float(depth_t))
            logdata += [float(data_t), float(data_t)]
        elif logdepth[-1] >= depth_t:
            logdepth = [l for l in logdepth if l < depth_t]
            logdata = [d for d, l in zip(logdata, logdepth) if l < depth_t]
            logdepth.append(float(depth_t))
            logdata.append(logdata[-1])
    logdepth = np.array(logdepth)
    logdepth = logdepth[4:]
    logdata = np.array(logdata)
    logdata = logdata[4:]
    return logdepth, logdata
