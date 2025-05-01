DROP VIEW IF EXISTS `Dim_Datum_Full`;
DROP TABLE IF EXISTS `Dim_Datum_Full`;

CREATE TABLE `Dim_Datum_Full` (
  `datum_id`      BIGINT     NOT NULL PRIMARY KEY,
  `full_datetime` DATETIME   NOT NULL
);

INSERT INTO `Dim_Datum_Full` (`datum_id`, `full_datetime`)
SELECT
  `datum_id`,
  TIMESTAMP(`datum`, MAKETIME(`stunde`, `minute`, 0))
FROM
  `Dim_Datum`;
