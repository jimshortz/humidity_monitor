CREATE TABLE IF NOT EXISTS `sensors` (
  `sensor_id` tinyint(4) NOT NULL,
  `feed` varchar(32) NOT NULL,
  PRIMARY KEY (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE TABLE `cycles` (
  `start_time` datetime NOT NULL,
  `off_time` datetime NOT NULL,
  `end_time` datetime NOT NULL,
  PRIMARY KEY (`end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE TABLE `daily` (
  `time` date NOT NULL,
  `sensor_id` tinyint(4) NOT NULL,
  `samples` int(11) NOT NULL,
  `min_value` decimal(6,2) NOT NULL,
  `avg_value` decimal(6,2) NOT NULL,
  `max_value` decimal(6,2) NOT NULL,
  PRIMARY KEY (`sensor_id`,`time`),
  CONSTRAINT `fk_daily_sensors` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;


CREATE TABLE `hourly` (
  `time` datetime NOT NULL,
  `sensor_id` tinyint(4) NOT NULL,
  `samples` int(11) NOT NULL,
  `min_value` decimal(6,2) NOT NULL,
  `avg_value` decimal(6,2) NOT NULL,
  `max_value` decimal(6,2) NOT NULL,
  PRIMARY KEY (`sensor_id`,`time`),
  CONSTRAINT `fk_hourly_sensors` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE TABLE `raw` (
  `time` datetime NOT NULL DEFAULT UTC_TIMESTAMP(),
  `sensor_id` tinyint(4) NOT NULL,
  `value` decimal(6,2) NOT NULL,
  PRIMARY KEY (`sensor_id`,`time`),
  CONSTRAINT `fk_raw_sensors` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci

-- Data

INSERT INTO `sensors` VALUES
(1,'indoor-humid'),
(2,'indoor-temp'),
(3,'power');
