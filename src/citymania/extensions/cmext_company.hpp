#ifndef CMEXT_COMPANY_HPP
#define CMEXT_COMPANY_HPP

#include "../../cargo_type.h"

#include <array>

namespace citymania {

namespace ext {

class CompanyEconomyEntry {
public:
    std::array<Money, NUM_CARGO> cargo_income{}; ///< Cargo income from each cargo type
};

class Company {
public:
    bool is_server;  ///< whether company is controlled by the server
    bool is_scored;  ///< whether company is eligible for scoring
};

} // namespace citymania

} // namespace citymania

#endif
