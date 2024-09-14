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
  `time` datetime NOT NULL,
  `sensor_id` tinyint(4) NOT NULL,
  `value` decimal(6,2) NOT NULL,
  PRIMARY KEY (`time`,`sensor_id`),
  CONSTRAINT `fk_raw_sensors` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE TABLE `alarms` (
  `id`                varchar(32) NOT NULL,
  `sensor_id`         tinyint(4) NULL,
  `aggregate`         ENUM('COUNT','MIN','MAX','AVG') NOT NULL,
  `window`            int NOT NULL, -- in seconds
  `min_value`         decimal(6,2) NULL,
  `max_value`         decimal(6,2) NULL,
  `message`           varchar(128) NOT NULL,
  `state`             ENUM('UNKNOWN','TOO_LOW','TOO_HIGH','HEALTHY') NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_alarms_sensors` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
  
-- Data

INSERT INTO `sensors` VALUES
(1,'indoor-humid'),
(2,'indoor-temp'),
(3,'power');

INSERT INTO `alarms` VALUES
('humid', 1, 'AVG', 15*60, 30, 55, 'Humidity', 'HEALTHY'),
('temp', 2, 'AVG', 15*60, 60, 85, 'Temperature', 'HEALTHY'),
('power', 3, 'AVG', 15*60, 0, 600, 'Power', 'HEALTHY'),
('dehumid', 3, 'MAX', 60*60, 200, NULL, 'Dehumidifer shutdown', 'HEALTHY');
