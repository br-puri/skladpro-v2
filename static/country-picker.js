/* Shared country selector. Names are saved as before, so existing documents
   and addresses retain their country text. Native selects support keyboard
   type-to-select and the platform's accessible scrollable picker. */
(() => {
  const codes = 'AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split(' ');
  if (!Intl.DisplayNames) return; // Older browsers keep the original editable field.
  const names = new Intl.DisplayNames(['en'], {type: 'region'});
  const countries = codes.map(code => names.of(code)).sort((a,b) => a.localeCompare(b));
  function init(root = document) {
    root.querySelectorAll('input[name="country"], input[name="co_country"], input[name="co_delivery_country"]').forEach(input => {
      const select = document.createElement('select');
      for (const attr of input.attributes) {
        if (!['type','value','placeholder'].includes(attr.name)) select.setAttribute(attr.name, attr.value);
      }
      select.dataset.countryPicker = 'true';
      select.setAttribute('aria-label', 'Country');
      select.autocomplete = 'country-name';
      select.add(new Option('Select country…', ''));
      const current = input.value;
      if (current && !countries.includes(current)) select.add(new Option(current, current));
      for (const country of countries) select.add(new Option(country, country));
      select.value = current;
      for (const option of select.options) option.defaultSelected = option.selected;
      input.replaceWith(select);
    });
  }
  window.initCountryPickers = init;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => init());
  else init();
})();
