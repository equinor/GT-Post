from gtpost.postprocess.sediment import get_d50input


def read_sedfile(sedfile):
    # read the sed def file and initialize sed type
    # specific density and dry bed density with an empty list
    sedtype = []
    rho_p = []
    rho_db = []
    sedfile_line = []
    with open(sedfile) as fobj:
        for i, line in enumerate(fobj):
            # read lines until SedType is found
            if "SedTyp" in line:
                temp = str(line.split()[2])  # retrieve sedtype
                sedtype.append(temp)
                sedfile_line.append(i)
            if "RhoSol" in line:
                temp = float(line.split()[2])  # retrieve specific density
                rho_p.append(temp)
            if "CDryB" in line:
                temp = float(line.split()[2])  # retrieve specific density
                rho_db.append(temp)

    d50_input = get_d50input(sedfile, sedtype, rho_p, sedfile_line)
    return sedtype, rho_p, rho_db, d50_input
