import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def revise(inidata):
    """
    update inidata from version 0.6.0 to 0.7.0 format
    :param inidata:
    :return:
    """
    if "template" in inidata:
        template = inidata["template"]["value"]
        if "River" in template:
            logger.info("input data is conform 0.7.0 format")
        else:
            logger.info("Template input %s found in input data" % template)
            if template.endswith("Basin fill"):
                inidata["waveheight"] = {"value": 0}
                inidata["test"] = {"value": "no-test"}
            elif "marine" in template:
                # set up a default waveheight value
                inidata["waveheight"] = {"value": 1}
                inidata["test"] = {"value": "no-test"}
            elif "Testing" in template:
                inidata["waveheight"] = {"value": 0}
                inidata["test"] = {"value": "test"}
            logger.info("waveheight input set to: %s" % inidata["waveheight"])
            logger.info("test input set to: %s" % inidata["test"])
            logger.info("template input removed from dictionary")
        del inidata["template"]
    else:
        logger.info("input data is conform 0.7.0 format")
    return inidata
